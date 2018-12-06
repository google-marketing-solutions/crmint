# Copyright 2018 Google Inc
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
import json
import re
import uuid
from google.appengine.api import taskqueue
from simpleeval import simple_eval
from simpleeval import InvalidExpression
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import load_only
from core import inline
from core.database import BaseModel
from core.mailers import NotificationMailer


def _parse_num(s):
  try:
    return int(s)
  except ValueError:
    try:
      return float(s)
    # TODO(dulacp) should raise a ValueError exception, not silence it
    except ValueError:
      return 0


class Pipeline(BaseModel):
  __tablename__ = 'pipelines'
  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String(255))
  emails_for_notifications = Column(String(255))
  status = Column(String(50), nullable=False, default='idle')
  status_changed_at = Column(DateTime)
  jobs = relationship('Job', backref='pipeline',
                      lazy='dynamic')
  run_on_schedule = Column(Boolean, nullable=False, default=False)
  schedules = relationship('Schedule', lazy='dynamic')
  params = relationship('Param', lazy='dynamic', order_by='asc(Param.name)')

  class STATUS(object):
    IDLE = 'idle'
    FAILED = 'failed'
    SUCCEEDED = 'succeeded'
    STOPPING = 'stopping'
    RUNNING = 'running'
    INACTIVE_STATUSES = [IDLE, FAILED, SUCCEEDED]

  def __init__(self, name=None):
    super(Pipeline, self).__init__()
    self.name = name

  @property
  def state(self):
    return self.status

  @property
  def has_jobs(self):
    return self.jobs.count() > 0

  @property
  def recipients(self):
    if self.emails_for_notifications:
      return self.emails_for_notifications.split()
    return []

  def assign_attributes(self, attributes):
    for key, value in attributes.iteritems():
      if key in ['schedules', 'jobs', 'params']:
        continue
      if key == 'run_on_schedule':
        self.__setattr__(key, value == 'True')
        continue
      self.__setattr__(key, value)

  def save_relations(self, relations):
    for key, value in relations.iteritems():
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
    try:
      global_context = {}
      for param in Param.where(pipeline_id=None, job_id=None).all():
        global_context[param.name] = param.populate_runtime_value()
      pipeline_context = global_context.copy()
      for param in self.params.all():
        pipeline_context[param.name] = param.populate_runtime_value(global_context)
      for job in self.jobs.all():
        for param in job.params.all():
          param.populate_runtime_value(pipeline_context)
      return True
    except (InvalidExpression, TypeError) as e:
      from core import cloud_logging
      job_id = '-'
      worker_class = '-'
      if param.job_id is not None:
        job_id = param.job_id
        worker_class = param.job.worker_class
        message = 'Bad job param "%s": %s' % (param.label, e)
      elif param.pipeline_id is not None:
        message = 'Bad pipeline param "%s": %s' % (param.label, e)
      else:
        message = 'Bad global param "%s": %s' % (param.label, e)
      cloud_logging.logger.log_struct({
          'labels': {
              'pipeline_id': self.id,
              'job_id': job_id,
              'worker_class': worker_class,
          },
          'log_level': 'ERROR',
          'message': message,
      })
      return False

  def set_status(self, status):
    self.update(status=status, status_changed_at=datetime.now())

  def get_ready(self):
    if not self.populate_params_runtime_values():
      return False
    for job in self.jobs.all():
      if not job.get_ready():
        return False
    self.set_status(Pipeline.STATUS.RUNNING)
    return True

  def start(self):
    if self.status not in Pipeline.STATUS.INACTIVE_STATUSES:
      return False

    jobs = self.jobs.all()
    if len(jobs) < 1:
      return False

    for job in jobs:
      if job.status not in Job.STATUS.INACTIVE_STATUSES:
        return False

    if not self.get_ready():
      return False

    for job in jobs:
      job.start()
    return True

  def _cancel_all_tasks(self):
    for job in self.jobs:
      job.cancel_tasks()

  def stop(self):
    if self.status != Pipeline.STATUS.RUNNING:
      return False
    for job in self.jobs:
      job.stop()
    for job in self.jobs:
      if job.status not in [Job.STATUS.FAILED, Job.STATUS.SUCCEEDED]:
        job.set_status(Job.STATUS.STOPPING)
    self._cancel_all_tasks()
    return self.job_finished()

  def start_single_job(self, job):
    if self.status not in Pipeline.STATUS.INACTIVE_STATUSES:
      return False
    if not self.populate_params_runtime_values():
      return False
    if not job.get_ready():
      return False
    self.set_status(Pipeline.STATUS.RUNNING)
    job.start()
    return True

  def job_finished(self):
    for job in self.jobs:
      if job.status == Job.STATUS.STOPPING:
        job.set_status(Job.STATUS.FAILED)
    for job in self.jobs:
      if job.status not in Job.STATUS.INACTIVE_STATUSES:
        return False
    self._finish()
    return True

  def _finish(self):
    jobs = Job.query.outerjoin((StartCondition,
                                Job.id == StartCondition.preceding_job_id))
    jobs = jobs.filter(Job.pipeline_id == self.id)
    jobs = jobs.filter(StartCondition.preceding_job_id == None)
    jobs = jobs.options(load_only('status')).all()
    status = Pipeline.STATUS.SUCCEEDED
    for job in jobs:
      # IDLE means the job has not run at all or it has been cancelled
      if job.status == Job.STATUS.FAILED:
        status = Pipeline.STATUS.FAILED
        break
    self.set_status(status)
    NotificationMailer().finished_pipeline(self)

  def import_data(self, data):
    self.assign_params(data['params'])
    self.assign_schedules(data['schedules'])
    job_mapping = {}
    jobs = []
    if data['jobs']:
      for job_data in data['jobs']:
        job = Job()
        job.pipeline_id = self.id
        job.assign_attributes(job_data)
        job.save()
        job.save_relations(job_data)
        jobs.append(job)
        job_mapping[job_data['id']] = job.id
      for job in jobs:
        job_id = job_mapping.keys()[job_mapping.values().index(job.id)]
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


class Job(BaseModel):
  __tablename__ = 'jobs'
  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String(255))
  status = Column(String(50), nullable=False, default='idle')
  status_changed_at = Column(DateTime)
  worker_class = Column(String(255))
  pipeline_id = Column(Integer, ForeignKey('pipelines.id'))
  params = relationship('Param', backref='job', lazy='dynamic')
  start_conditions = relationship(
      'StartCondition',
      primaryjoin='Job.id==StartCondition.job_id')
  dependent_jobs = relationship(
      'Job',
      secondary='start_conditions',
      primaryjoin='Job.id==StartCondition.preceding_job_id',
      secondaryjoin='StartCondition.job_id==Job.id')

  class STATUS(object):
    IDLE = 'idle'
    FAILED = 'failed'
    SUCCEEDED = 'succeeded'
    RUNNING = 'running'
    WAITING = 'waiting'
    STOPPING = 'stopping'
    INACTIVE_STATUSES = [IDLE, FAILED, SUCCEEDED]

  def __init__(self, name=None, worker_class=None, pipeline_id=None):
    super(Job, self).__init__()
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

  def get_ready(self):
    if self.status not in Job.STATUS.INACTIVE_STATUSES:
      return False
    self.set_status(Job.STATUS.WAITING)
    return True

  def _get_task_namespace(self):
    return 'pipeline=%s_job=%s' % (str(self.pipeline_id), str(self.id))

  def _add_task_with_name(self, task_name):
    task_namespace = self._get_task_namespace()
    TaskEnqueued.create(task_namespace=task_namespace, task_name=task_name)
    return True

  def _delete_task_with_name(self, task_name):
    """
    Returns: Number of remaining tasks in the DB.
    """
    task_namespace = self._get_task_namespace()
    TaskEnqueued.where(task_namespace=task_namespace,
                       task_name=task_name).delete()
    return self._enqueued_task_count()

  def cancel_tasks(self):
    task_namespace = self._get_task_namespace()
    enqueued_tasks = TaskEnqueued.where(task_namespace=task_namespace)
    if enqueued_tasks:
      tasks = [taskqueue.Task(name=t.task_name) for t in enqueued_tasks]
      taskqueue.Queue().delete_tasks(tasks)
      TaskEnqueued.where(task_namespace=task_namespace).delete()

  def _enqueued_task_count(self):
    task_namespace = self._get_task_namespace()
    return TaskEnqueued.count_in_namespace(task_namespace)

  def _start_condition_is_fulfilled(self, start_condition):
    preceding_job_status = start_condition.preceding_job.status
    if start_condition.condition == StartCondition.CONDITION.SUCCESS:
      if preceding_job_status == Job.STATUS.FAILED:
        return False
    elif start_condition.condition == StartCondition.CONDITION.FAIL:
      if preceding_job_status == Job.STATUS.SUCCEEDED:
        return False
    return True

  def start(self):
    """
    Returns: Task object that was added to the task queue, otherwise None.
    """
    # Validates that preceding jobs fulfill the starting conditions.
    for start_condition in self.start_conditions:
      if self._start_condition_is_fulfilled(start_condition):
        if start_condition.preceding_job.status not in [
            Job.STATUS.SUCCEEDED,
            Job.STATUS.FAILED]:
          return None
      else:
        # pipeline failure
        self.set_status(Job.STATUS.FAILED)
        self.pipeline.update(status=Pipeline.STATUS.FAILED,
                             status_changed_at=datetime.now())
        self.pipeline.stop()
        return None

    if self.pipeline.status == Pipeline.STATUS.FAILED:
      return None

    if self.status != Job.STATUS.WAITING:
      return None
    else:
      self.set_status(Job.STATUS.RUNNING)
      return self.run()

  def run(self):
    worker_params = dict([(p.name, p.worker_value) for p in self.params])
    return self.enqueue(self.worker_class, worker_params)

  def stop(self):
    self.cancel_tasks()
    if self.status == Job.STATUS.WAITING:
      self.set_status(Job.STATUS.IDLE)
      return True
    elif self.status == Job.STATUS.RUNNING:
      self.set_status(Job.STATUS.STOPPING)
      return True
    return False

  def enqueue(self, worker_class, worker_params, delay=0):
    if self.status != Job.STATUS.RUNNING:
      return None

    # Add a new task to the queue.
    task_name = '%s_%s' % (self.pipeline.id, self.id)
    escaped_task_name = re.sub(r'[^-_0-9a-zA-Z]', '-', task_name)
    unique_task_name = '%s_%s' % (escaped_task_name, str(uuid.uuid4()))
    task_params = {
        'job_id': self.id,
        'worker_class': worker_class,
        'worker_params': json.dumps(worker_params),
        'task_name': unique_task_name
    }
    task = taskqueue.add(
        target='job-service',
        name=unique_task_name,
        url='/task',
        params=task_params,
        countdown=delay)

    # Keep track of the running task name.
    self._add_task_with_name(unique_task_name)
    self.save()

    return task

  def _start_dependent_jobs(self):
    if self.dependent_jobs:
      for job in self.dependent_jobs:
        job.start()

  def set_status(self, status):
    self.update(status=status, status_changed_at=datetime.now())

  def _task_completed(self, task_name):
    """Completes task execution.

    Returns: True if it was the last tasks to be completed. False otherwise.
    """
    remaining_tasks = self._delete_task_with_name(task_name)
    return remaining_tasks == 0

  def task_succeeded(self, task_name):
    was_last_task = self._task_completed(task_name)
    # Updates the job database status if there is no more running tasks.
    # NB: `was_last_task` acts as a concurrent lock, only one task can
    #     validate this condition.
    if was_last_task:
      # Cancel all tasks if one condition doesn't match the success status.
      for job in self.dependent_jobs:
        for start_condition in job.start_conditions:
          success_statuses = [
              StartCondition.CONDITION.SUCCESS,
              StartCondition.CONDITION.WHATEVER
          ]
          if (start_condition.preceding_job.id == self.id
              and start_condition.condition not in success_statuses):
            self.set_status(Job.STATUS.SUCCEEDED)
            return self.pipeline.stop()
      self.set_status(Job.STATUS.SUCCEEDED)
      # We can safely start children jobs, because of our concurrent lock.
      self._start_dependent_jobs()
      self.pipeline.job_finished()

  def task_failed(self, task_name):
    was_last_task = self._task_completed(task_name)

    # If no dependent jobs then the pipeline failed
    if not self.dependent_jobs:
      self.set_status(Job.STATUS.FAILED)
      return self.pipeline.stop()

    # Cancel all tasks if one condition doesn't match the failed status.
    for job in self.dependent_jobs:
      for start_condition in job.start_conditions:
        failed_statuses = [
            StartCondition.CONDITION.FAIL,
            StartCondition.CONDITION.WHATEVER
        ]
        if (start_condition.preceding_job.id == self.id
            and start_condition.condition not in failed_statuses):
          self.set_status(Job.STATUS.FAILED)
          return self.pipeline.stop()

    if was_last_task:
      self.set_status(Job.STATUS.FAILED)
      # We can safely start children jobs, because of our concurrent lock.
      self._start_dependent_jobs()
      self.pipeline.job_finished()

  def assign_attributes(self, attributes):
    for key, value in attributes.iteritems():
      if key in ['params', 'start_conditions', 'id', 'hash_start_conditions']:
        continue
      self.__setattr__(key, value)

  def save_relations(self, relations):
    for key, value in relations.iteritems():
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

    arg_sc_ids = set([sc['id'] for sc in scs])
    cur_sc_ids = set([sc.preceding_job_id for sc in self.start_conditions])

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


class Param(BaseModel):
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

  _INLINER_REGEX = re.compile(r'{%.+?%}')

  def populate_runtime_value(self, context={}):
    names = context.copy()
    names.update({'True': True, 'False': False})
    value = self.value
    inliners = self._INLINER_REGEX.findall(value)
    for inliner in inliners:
      result = simple_eval(inliner[2:-2], functions=inline.functions,
                           names=names)
      value = value.replace(inliner, str(result))
    if self.job_id is not None:
      self.update(runtime_value=value)
    return value

  @property
  def worker_value(self):
    if self.type == 'boolean':
      return self.runtime_value == '1'
    if self.type == 'number':
      return _parse_num(self.runtime_value)
    if self.type == 'string_list':
      return self.runtime_value.split('\n')
    if self.type == 'number_list':
      return [_parse_num(l) for l in self.runtime_value.split('\n') if l.strip()]
    return self.runtime_value

  @property
  def api_value(self):
    if self.type == 'boolean':
      return self.value == '1'
    return self.value

  def __init__(self, name=None, type=None):
    self.name = name
    self.type = type

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
        if obj and obj.__class__.__name__ == 'Pipeline':
          param.pipeline_id = obj.id
        elif obj and obj.__class__.__name__ == 'Job':
          param.job_id = obj.id
      param.name = arg_param['name']
      param.type = arg_param['type']
      if arg_param['type'] == 'boolean':
        param.value = arg_param['value']
      else:
        param.value = arg_param['value'].encode('utf-8')
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


class StartCondition(BaseModel):
  __tablename__ = 'start_conditions'
  id = Column(Integer, primary_key=True, autoincrement=True)
  job_id = Column(Integer, ForeignKey('jobs.id'))
  preceding_job_id = Column(Integer, ForeignKey('jobs.id'))
  condition = Column(String(255))

  job = relationship('Job', foreign_keys=[job_id])
  preceding_job = relationship('Job', foreign_keys=[preceding_job_id])

  class CONDITION(object):
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


class Schedule(BaseModel):
  __tablename__ = 'schedules'
  id = Column(Integer, primary_key=True, autoincrement=True)
  pipeline_id = Column(Integer, ForeignKey('pipelines.id'))
  cron = Column(String(255))

  pipeline = relationship('Pipeline', foreign_keys=[pipeline_id])


class GeneralSetting(BaseModel):
  __tablename__ = 'general_settings'
  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String(255))
  value = Column(Text())


class Stage(BaseModel):
  __tablename__ = 'stages'
  id = Column(Integer, primary_key=True, autoincrement=True)
  sid = Column(String(255))

  def assign_attributes(self, attributes):
    for key, value in attributes.iteritems():
      self.__setattr__(key, value)


class TaskEnqueued(BaseModel):
  __tablename__ = 'enqueued_tasks'
  id = Column(Integer, primary_key=True, autoincrement=True)
  task_namespace = Column(String(60), index=True)
  task_name = Column(String(100), index=True, unique=True)

  @classmethod
  def count_in_namespace(cls, task_namespace):
    count_query = cls.where(task_namespace=task_namespace)
    return count_query.count()
