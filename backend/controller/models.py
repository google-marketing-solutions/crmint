# Copyright 2020 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
import numbers
import re
from typing import Union
import uuid

import jinja2
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import orm
from sqlalchemy import String
from sqlalchemy import Text

from common import crmint_logging
from common import task
from controller import database
from controller import inline
from controller import mailers


def _str_to_number(x: str) -> numbers.Number:
  """Converts the input string into a number.

  Args:
    x: String containing the numerical value to parse (e.g. '3' or '2.75').

  Returns:
    Parsed input value as a number type.

  Raises:
    ValueError: if the input is neither a valid literal `int` nor a `float`.
  """
  try:
    return int(x)
  except ValueError:
    return float(x)


class Pipeline(database.BaseModel):
  """Pipeline ORM class."""
  __tablename__ = 'pipelines'
  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String(255))
  emails_for_notifications = Column(String(255))
  status = Column(String(50), nullable=False, default='idle')
  status_changed_at = Column(DateTime)
  jobs = orm.relationship(
      'Job', backref='pipeline', lazy='dynamic')
  run_on_schedule = Column(Boolean, nullable=False, default=False)
  schedules = orm.relationship(
      'Schedule', lazy='dynamic', back_populates='pipeline')
  params = orm.relationship('Param', lazy='dynamic', order_by='asc(Param.name)')

  class STATUS:  # pylint: disable=too-few-public-methods
    """Pipeline statuses."""
    IDLE = 'idle'
    FAILED = 'failed'
    SUCCEEDED = 'succeeded'
    STOPPING = 'stopping'
    RUNNING = 'running'
    INACTIVE_STATUSES = [IDLE, FAILED, SUCCEEDED]

  def __init__(self, name=None):
    super().__init__()
    self.name = name

  @property
  def has_jobs(self):
    return self.jobs.count() > 0

  @property
  def recipients(self):
    if self.emails_for_notifications:
      return self.emails_for_notifications.split()
    return []

  def assign_attributes(self, attributes):
    for key, value in attributes.items():
      if key in ['schedules', 'jobs', 'params']:
        continue
      if key == 'run_on_schedule':
        self.__setattr__(key, value == 'True')
        continue
      self.__setattr__(key, value)

  def save_relations(self, relations):
    for key, value in relations.items():
      if key == 'schedules':
        self.assign_schedules(value)
      elif key == 'params':
        self.assign_params(value)

  def assign_params(self, parameters):
    Param.update_list(parameters, self)

  def assign_schedules(self, arg_schedules):
    # Remove if records not in list ids for update
    arg_schedule_ids = []
    for arg_schedule in arg_schedules:
      if arg_schedule.get('id') is not None:
        # Updating
        schedule = Schedule.find(arg_schedule.get('id'))
        schedule.update(cron=arg_schedule['cron'])
        arg_schedule_ids.append(arg_schedule['id'])
      else:
        # Creating
        schedule = Schedule.create(pipeline_id=self.id,
                                   cron=arg_schedule['cron'])
        arg_schedule_ids.append(schedule.id)
    # Removing
    ids_for_removing = []
    for schedule in self.schedules:
      if schedule.id not in arg_schedule_ids:
        ids_for_removing.append(schedule.id)
    Schedule.destroy(*ids_for_removing)

  def populate_params_runtime_values(self):
    inline.open_session()
    try:
      global_context = {}
      for param in Param.where(pipeline_id=None, job_id=None).all():
        global_context[param.name] = param.populate_runtime_value()
      pipeline_context = global_context.copy()
      for param in self.params.all():
        pipeline_context[param.name] = param.populate_runtime_value(
            global_context)
      for job in self.jobs.all():
        for param in job.params.all():
          param.populate_runtime_value(pipeline_context)
      inline.close_session()
      return True
    except (jinja2.exceptions.TemplateError, TypeError, ValueError) as e:
      inline.close_session()
      job_id = 'N/A'
      worker_class = 'N/A'
      if param.job_id is not None:
        job_id = param.job_id
        worker_class = param.job.worker_class
        message = 'Invalid job parameter "%s": %s' % (param.label, e)
      elif param.pipeline_id is not None:
        message = 'Invalid pipeline variable "%s": %s' % (param.label, e)
      else:
        message = 'Invalid global variable "%s": %s' % (param.label, e)
      crmint_logging.log_message(
          message,
          log_level='ERROR',
          pipeline_id=self.id,
          job_id=job_id,
          worker_class=worker_class)
      return False

  def set_status(self, status):
    self.update(status=status, status_changed_at=datetime.now())

  def get_ready(self) -> bool:
    """Returns True if the pipeline is ready to be started."""
    if self.status not in Pipeline.STATUS.INACTIVE_STATUSES:
      return False
    # Checks if there is at least one job to run.
    if not self.jobs.all():
      return False
    # Checks if one job was already started.
    for job in self.jobs.all():
      if not job.get_ready():
        return False
    # Checks that parameters can be rendered to runtime values.
    if not self.populate_params_runtime_values():
      return False
    return True

  def start(self):
    if not self.get_ready():
      return False
    self.set_status(Pipeline.STATUS.RUNNING)
    for job in self.jobs.all():
      job.start()
    return True

  def stop(self):
    if self.status != Pipeline.STATUS.RUNNING:
      return False
    for job in self.jobs.all():
      job.stop()
    self.set_status(Pipeline.STATUS.IDLE)
    return True

  def start_single_job(self, job):
    if self.status not in Pipeline.STATUS.INACTIVE_STATUSES:
      return False
    if not self.populate_params_runtime_values():
      return False
    if not job.get_ready():
      return False
    self.set_status(Pipeline.STATUS.RUNNING)
    job.start_as_single()
    return True

  def has_finished(self) -> bool:
    """Returns True if a pipeline is in a finished state.

    A pipeline is considered finished when all jobs are in an inactive status.
    """
    for job in self.jobs.all():
      if job.status not in Job.STATUS.INACTIVE_STATUSES:
        return False
    return True

  def has_failed(self) -> bool:
    """Returns True if a pipeline is in a failed state.

    A pipeline is considered failed if one of these two conditions is met:
      1. an isolated job failed
      2. or one starting condition is not fulfilled
    """
    for job in self.jobs.all():
      # 1. Checks if an isolated job has failed.
      if not job.dependent_jobs and not job.affecting_jobs:
        if job.status == Job.STATUS.FAILED:
          return True
      # 2. Checks if a starting condition has been invalidated.
      for start_condition in job.start_conditions:
        if job.start_condition_invalidated(start_condition):
          return True
    return False

  # TODO(dulacp): rename this method to `job_finished`
  def leaf_job_finished(self) -> None:
    """Determines if the pipeline should be considered finished or failed."""
    pipeline_failed = self.has_failed()
    pipeline_finished = self.has_finished()
    if pipeline_failed or pipeline_finished:
      status = Pipeline.STATUS.FAILED if pipeline_failed else Pipeline.STATUS.SUCCEEDED
      self.stop()
      self.set_status(status)
      mailers.NotificationMailer().finished_pipeline(self)

  def import_data(self, data):
    self.assign_params(data['params'])
    self.assign_schedules(data['schedules'])
    job_mapping = {}
    jobs = []
    if data['jobs']:
      for job_data in data['jobs']:
        job = Job.create()
        job.pipeline_id = self.id
        job.assign_attributes(job_data)
        job.save()
        job.save_relations(job_data)
        jobs.append(job)
        job_mapping[job_data['id']] = job.id
      for job in jobs:
        index = list(job_mapping.values()).index(job.id)
        job_id = list(job_mapping.keys())[index]
        job_data = next((j for j in data['jobs'] if j['id'] == job_id), None)
        job.assign_hash_start_conditions(job_data['hash_start_conditions'],
                                         job_mapping)

  def is_blocked(self):
    return (self.run_on_schedule or
            self.status in [Pipeline.STATUS.RUNNING, Pipeline.STATUS.STOPPING])

  def destroy(self):
    sc_ids = [sc.id for sc in self.schedules]
    if sc_ids:
      Schedule.destroy(*sc_ids)

    for job in self.jobs:
      job.destroy()

    param_ids = [p.id for p in self.params.all()]
    if param_ids:
      Param.destroy(*param_ids)
    self.delete()


class TaskEnqueued(database.BaseModel):
  __tablename__ = 'enqueued_tasks'
  id = Column(Integer, primary_key=True, autoincrement=True)
  task_namespace = Column(String(60), index=True)
  task_name = Column(String(100), index=True, unique=True)

  @classmethod
  def count_in_namespace(cls, task_namespace: str) -> int:
    """Returns the number of tasks still running in the given namespace."""
    count_query = cls.where(task_namespace=task_namespace)
    return count_query.count()

  @property
  def name(self):
    """TODO(dulacp): remove this helper, used to avoid too much refactoring."""
    return self.task_name


class StartCondition(database.BaseModel):
  __tablename__ = 'start_conditions'
  id = Column(Integer, primary_key=True, autoincrement=True)
  job_id = Column(Integer, ForeignKey('jobs.id'))
  preceding_job_id = Column(Integer, ForeignKey('jobs.id'))
  condition = Column(String(255))

  job = orm.relationship(
      'Job',
      foreign_keys=[job_id],
      back_populates='start_conditions',
      overlaps='affecting_jobs,dependent_jobs')
  preceding_job = orm.relationship(
      'Job',
      foreign_keys=[preceding_job_id],
      back_populates='affected_conditions',
      overlaps='affecting_jobs,dependent_jobs')

  class CONDITION:  # pylint: disable=too-few-public-methods
    SUCCESS = 'success'
    FAIL = 'fail'
    WHATEVER = 'whatever'

  def __init__(self, job_id=None, preceding_job_id=None, condition=None):
    self.job_id = job_id
    self.preceding_job_id = preceding_job_id
    self.condition = condition

  @property
  def preceding_job_name(self):
    return self.preceding_job.name

  @property
  def value(self):
    return ','.join([str(self.preceding_job_id), self.condition])

  @classmethod
  def parse_value(cls, value):
    return {
        'id': int(value['preceding_job_id']),
        'condition': value['condition']
    }


class Job(database.BaseModel):
  __tablename__ = 'jobs'
  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String(255))
  status = Column(String(50), nullable=False, default='idle')
  status_changed_at = Column(DateTime)
  worker_class = Column(String(255))
  pipeline_id = Column(Integer, ForeignKey('pipelines.id'))
  params = orm.relationship('Param', backref='job', lazy='dynamic')
  start_conditions = orm.relationship(
      'StartCondition',
      primaryjoin='Job.id==StartCondition.job_id',
      back_populates='job')
  affected_conditions = orm.relationship(
      'StartCondition',
      primaryjoin='Job.id==StartCondition.preceding_job_id',
      back_populates='preceding_job')
  dependent_jobs = orm.relationship(
      'Job',
      secondary='start_conditions',
      primaryjoin='Job.id==StartCondition.preceding_job_id',
      secondaryjoin='StartCondition.job_id==Job.id',
      back_populates='affecting_jobs',
      overlaps='affected_conditions,start_conditions')
  affecting_jobs = orm.relationship(
      'Job',
      secondary='start_conditions',
      primaryjoin='Job.id==StartCondition.job_id',
      secondaryjoin='StartCondition.preceding_job_id==Job.id',
      back_populates='dependent_jobs',
      overlaps='affected_conditions,start_conditions')

  class STATUS:  # pylint: disable=too-few-public-methods
    IDLE = 'idle'
    FAILED = 'failed'
    SUCCEEDED = 'succeeded'
    RUNNING = 'running'
    WAITING = 'waiting'
    STOPPING = 'stopping'
    INACTIVE_STATUSES = [IDLE, FAILED, SUCCEEDED]

  def __init__(self, name=None, worker_class=None, pipeline_id=None):
    super().__init__()
    self.name = name
    self.worker_class = worker_class
    self.pipeline_id = pipeline_id

  def destroy(self):
    sc_ids = [sc.id for sc in self.start_conditions]
    if sc_ids:
      StartCondition.destroy(*sc_ids)

    dependent_job_sc_ids = [
        sc.id for sc in StartCondition.where(preceding_job_id=self.id).all()]
    if dependent_job_sc_ids:
      StartCondition.destroy(*dependent_job_sc_ids)

    param_ids = [p.id for p in self.params.all()]
    if param_ids:
      Param.destroy(*param_ids)
    self.delete()

  def assign_attributes(self, attributes):
    for key, value in attributes.items():
      if key in ['params', 'start_conditions', 'id', 'hash_start_conditions']:
        continue
      self.__setattr__(key, value)

  def save_relations(self, relations):
    for key, value in relations.items():
      if key == 'params':
        self.assign_params(value)
      elif key == 'start_conditions':
        self.assign_start_conditions(value)

  def add_start_conditions(self, items):
    for item in items:
      self.start_conditions.append(item)

  def assign_params(self, parameters):
    Param.update_list(parameters, self)

  def assign_hash_start_conditions(self, arg_start_conditions, job_mapping):
    for arg_start_condition in arg_start_conditions:
      preceding_job_id = job_mapping[arg_start_condition['preceding_job_id']]
      StartCondition.create(
          job_id=self.id,
          preceding_job_id=preceding_job_id,
          condition=arg_start_condition['condition']
      )

  def assign_start_conditions(self, arg_start_conditions):
    scs = []
    for arg_start_condition in arg_start_conditions:
      scs.append(StartCondition.parse_value(arg_start_condition))

    arg_sc_ids = {sc['id'] for sc in scs}
    cur_sc_ids = {sc.preceding_job_id for sc in self.start_conditions}

    sc_intersection_ids = set(arg_sc_ids) & set(cur_sc_ids)
    new_sc_ids = set(arg_sc_ids) - set(cur_sc_ids)
    for v in scs:
      # Add new start conditions
      if v['id'] in new_sc_ids:
        StartCondition.create(
            job_id=self.id,
            preceding_job_id=v['id'],
            condition=v['condition']
        )
      # Update current start conditions
      elif v['id'] in sc_intersection_ids:
        sc = StartCondition.where(
            job_id=self.id,
            preceding_job_id=v['id']
        ).first()
        sc.condition = v['condition']
        sc.save()
    # Delete extra start conditions
    delete_sc_ids = set(cur_sc_ids) - set(arg_sc_ids)
    StartCondition.where(
        job_id=self.id,
        preceding_job_id__in=delete_sc_ids
    ).delete(synchronize_session=False)

  def set_status(self, status):
    self.update(status=status, status_changed_at=datetime.now())

  def get_ready(self) -> bool:
    """Returns True if the job is ready to be started."""
    if self.status not in Job.STATUS.INACTIVE_STATUSES:
      return False
    self.set_status(Job.STATUS.WAITING)
    return True

  def start_condition_invalidated(self,
                                  start_condition: StartCondition) -> bool:
    if start_condition.preceding_job.status not in Job.STATUS.INACTIVE_STATUSES:
      # Still running
      return False
    return not self._start_condition_is_fulfilled(start_condition)

  def _start_condition_is_fulfilled(self, start_condition) -> bool:
    preceding_job_status = start_condition.preceding_job.status
    if start_condition.condition == StartCondition.CONDITION.SUCCESS:
      if preceding_job_status != Job.STATUS.SUCCEEDED:
        return False
    elif start_condition.condition == StartCondition.CONDITION.FAIL:
      if preceding_job_status == Job.STATUS.SUCCEEDED:
        return False
    return True

  def _start_dependent_jobs(self) -> list[TaskEnqueued]:
    enqueued_tasks = []
    for job in self.dependent_jobs:
      started_task = job.start()
      if started_task:
        enqueued_tasks.append(started_task)
    return enqueued_tasks

  def start(self) -> Union[TaskEnqueued, None]:
    for start_condition in self.start_conditions:
      if start_condition.preceding_job.status not in Job.STATUS.INACTIVE_STATUSES:
        # Starting condition still running.
        return None
      if not self._start_condition_is_fulfilled(start_condition):
        # Cannot start this job, pipeline has failed.
        self.pipeline.leaf_job_finished()
        return None
    return self.start_as_single()

  def start_as_single(self) -> Union[TaskEnqueued, None]:
    if self.status != Job.STATUS.WAITING:
      # Either `job.get_ready()` wasn't called or it failed.
      return None
    self.set_status(Job.STATUS.RUNNING)
    worker_params = {p.name: p.worker_value for p in self.params}
    return self.enqueue(self.worker_class, worker_params)

  def _get_task_namespace(self):
    return f'pipeline={self.pipeline_id}_job={self.id}'

  def _add_task_with_name(self, task_name) -> TaskEnqueued:
    """Keeps track of running tasks."""
    namespace = self._get_task_namespace()
    return TaskEnqueued.create(task_namespace=namespace, task_name=task_name)

  def _delete_task_with_name(self, task_name):
    """Returns the number of remaining tasks in the DB after deletion."""
    task_namespace = self._get_task_namespace()
    TaskEnqueued.where(task_namespace=task_namespace,
                       task_name=task_name).delete()
    return self._enqueued_task_count()

  def _get_all_tasks(self):
    task_namespace = self._get_task_namespace()
    return TaskEnqueued.where(task_namespace=task_namespace).all()

  def _enqueued_task_count(self):
    task_namespace = self._get_task_namespace()
    return TaskEnqueued.count_in_namespace(task_namespace)

  def enqueue(self,
              worker_class: str,
              worker_params: dict[str, ...],
              delay: int = 0) -> Union[TaskEnqueued, None]:
    if self.status != Job.STATUS.RUNNING:
      return None
    name = str(uuid.uuid4())
    general_settings = {gs.name: gs.value for gs in GeneralSetting.all()}
    task_inst = task.Task(
        name,
        self.pipeline_id,
        self.id,
        worker_class,
        worker_params,
        general_settings)
    task_inst.enqueue(delay)
    return self._add_task_with_name(name)

  def _task_finished(self,
                     task_name: str,
                     new_job_status: str) -> list[TaskEnqueued]:
    """Records the task finishing state.

    If a job has spinned multiple tasks, we will only consider the status of
    the last task to complete.

    Args:
      task_name: Name of the task in our database.
      new_job_status: Status of the finished task.

    Returns:
      List of dependent tasks enqueued.
    """
    was_last_task = self._delete_task_with_name(task_name) == 0
    # Updates the job database status if there is no more running tasks.
    # This is essential because one job could spin multiple tasks.
    # NOTE: `was_last_task` acts as a kind of concurrent lock, only one task can
    #       validate this condition.
    # NOTE: if a job has spinned multiple tasks, we will only consider the
    #       status of the last task to complete.
    if was_last_task:
      self.set_status(new_job_status)
      # We can safely start children jobs, because of our above concurrent lock.
      if self.dependent_jobs:
        return self._start_dependent_jobs()
      else:
        self.pipeline.leaf_job_finished()
    return []

  def task_succeeded(self, task_name: str) -> list[TaskEnqueued]:
    return self._task_finished(task_name, Job.STATUS.SUCCEEDED)

  def task_failed(self, task_name: str) -> list[TaskEnqueued]:
    return self._task_finished(task_name, Job.STATUS.FAILED)

  def stop(self):
    if self.status == Job.STATUS.WAITING:
      self.set_status(Job.STATUS.IDLE)
      return True
    if self.status == Job.STATUS.RUNNING:
      self.set_status(Job.STATUS.STOPPING)
      tasks = self._get_all_tasks()
      for task_to_stop in tasks:
        self._task_finished(task_to_stop.name, Job.STATUS.STOPPING)
      return True
    return False


class Param(database.BaseModel):
  __tablename__ = 'params'
  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String(255), nullable=False)
  type = Column(String(50), nullable=False)
  pipeline_id = Column(Integer, ForeignKey('pipelines.id'))
  job_id = Column(Integer, ForeignKey('jobs.id'))
  is_required = Column(Boolean, nullable=False, default=False)
  description = Column(Text)
  label = Column(String(255))
  value = Column(Text())
  runtime_value = Column(Text())

  def populate_runtime_value(self, context=None):
    if context is None:
      context = {}
    # Leverages jinja2 templating system to render inline functions.
    content = self.value
    # Supports former syntax which used `{% ... %}` instead of `{{ ... }}`,
    # by substituting only patterns of uppercase variable names.
    content = re.sub(r'{% ([A-Z0-9]+) %}', r'{{ \1 }}', content)
    template = jinja2.Template(content, undefined=jinja2.StrictUndefined)
    value = template.render(**inline.functions, **context)
    if self.job_id is not None:
      self.update(runtime_value=value)
    return value

  @property
  def worker_value(self):
    if self.type == 'boolean':
      return self.runtime_value == '1'
    if self.type == 'number':
      return _str_to_number(self.runtime_value)
    if self.type == 'string_list':
      return self.runtime_value.split('\n')
    if self.type == 'number_list':
      return [
          _str_to_number(x)
          for x in self.runtime_value.split('\n')
          if x.strip()
      ]
    return self.runtime_value

  @property
  def api_value(self):
    if self.type == 'boolean':
      return self.value == '1'
    return self.value

  def __init__(self, name=None, param_type=None):
    self.name = name
    self.type = param_type

  @classmethod
  def update_list(cls, parameters, obj=None):
    arg_param_ids = []
    for arg_param in parameters:
      param = None
      if arg_param.get('id') is not None:
        # Updating
        param = Param.find(arg_param.get('id'))
      else:
        # Creating
        param = Param()
        if obj and isinstance(obj, Pipeline):
          param.pipeline_id = obj.id
        elif obj and isinstance(obj, Job):
          param.job_id = obj.id
      param.name = arg_param['name']
      try:
        param.label = arg_param['label']
      except KeyError:
        param.label = arg_param['name']
      param.type = arg_param['type']
      if arg_param['type'] == 'boolean':
        param.value = arg_param['value']
      else:
        param.value = str(arg_param['value'])
      param.save()
      arg_param_ids.append(param.id)
    # Removing
    ids_for_removing = []
    params = obj.params if obj else Param.where(pipeline_id=None,
                                                job_id=None).all()
    for param in params:
      if param.id not in arg_param_ids:
        ids_for_removing.append(param.id)
    Param.destroy(*ids_for_removing)


class Schedule(database.BaseModel):  # pylint: disable=too-few-public-methods
  __tablename__ = 'schedules'
  id = Column(Integer, primary_key=True, autoincrement=True)
  pipeline_id = Column(Integer, ForeignKey('pipelines.id'))
  cron = Column(String(255))

  pipeline = orm.relationship(
      'Pipeline', foreign_keys=[pipeline_id], back_populates='schedules')


class GeneralSetting(database.BaseModel):  # pylint: disable=too-few-public-methods
  __tablename__ = 'general_settings'
  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String(255))
  value = Column(Text())


class Stage(database.BaseModel):  # pylint: disable=too-few-public-methods
  __tablename__ = 'stages'
  id = Column(Integer, primary_key=True, autoincrement=True)
  sid = Column(String(255))

  def assign_attributes(self, attributes):
    for key, value in attributes.items():
      self.__setattr__(key, value)
