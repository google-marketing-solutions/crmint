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
from google.appengine.api import memcache
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
from core.database import BaseModel
from core import inline
from core.mailers import NotificationMailer

MEMCACHE_DEFAULT_EXPIRATION_TIME = 24 * 60 * 60

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

  def __init__(self, name=None):
    self.name = name
    cached_values = {
      "failed_jobs": 0, 
      "remaining_jobs": len(self.jobs.all()), 
      "list_of_tasks_enqueued": []
    }
    self._add_multi_to_memcache(cached_values)


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

  def _add_multi_to_memcache(self, mapping,retries = 10, time = MEMCACHE_DEFAULT_EXPIRATION_TIME):
    """
        Set multiple values in memcache, prefixed by the id of the pipeline
        and having a default expiration time of 24 hours
    """
    client = memcache.Client()
    while retries > 0:
      cached_mapping = client.get_multi(mapping, key_prefix = str(self.id) + "_", for_cas = True)
      if cached_mapping is None: 
        client.set_multi(mapping, key_prefix = str(self.id) + "_", time = time)
        return True
      if client.cas_multi(mapping, key_prefix = str(self.id) + "_", time = time):
        return True
      retries -= 1

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

  def get_ready(self):
    cache_values = {
      "failed_jobs": 0,
      "remaining_jobs": len(self.jobs.all()),
      "list_of_tasks_enqueued": []
    }
    self._add_multi_to_memcache(cache_values)

  def start(self):
    if self.status not in ['idle', 'finished', 'failed', 'succeeded']:
      return False
    self.get_ready()
    jobs = self.jobs.all()
    if len(jobs) < 1:
      return False
    for job in jobs:
      if job.get_status() not in ['idle', 'succeeded', 'failed']:
        return False
    for job in jobs:
      if not job.get_ready():
        return False
    for job in jobs:
      job.start()
    self.update(status='running', status_changed_at=datetime.now())
    return True

  def stop(self):
    if self.status != 'running':
      return False
    for job in self.jobs:
      job.stop()
    for job in self.jobs:
      if job.get_status() not in ['succeeded', 'failed']:
        self.update(status='stopping', status_changed_at=datetime.now())
        return True
    self._finish()
    return True

  def start_single_job(self, job):
    if self.status not in ['idle', 'finished', 'failed', 'succeeded']:
      return False
    job.run()
    self.update(status='running', status_changed_at=datetime.now())
    return True

  def job_finished(self):
    for job in self.jobs:
      if job.get_status() not in ['succeeded', 'failed', 'idle']:
        return False
    self._finish()
    return True

  def _finish(self):
    jobs = Job.query.outerjoin((StartCondition,
                                Job.id == StartCondition.preceding_job_id))
    jobs = jobs.filter(Job.pipeline_id == self.id)
    jobs = jobs.filter(StartCondition.preceding_job_id == None)
    jobs = jobs.options(load_only('status')).all()
    status = 'succeeded'
    for job in jobs:
      if job.get_status() == 'failed':
        status = 'failed'
        break
    self.update(status=status, status_changed_at=datetime.now())
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
    return (self.run_on_schedule or self.status in ['running', 'stopping'])

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
  enqueued_workers_count = Column(Integer, default=0)
  succeeded_workers_count = Column(Integer, default=0) #TODO remove
  failed_workers_count = Column(Integer, default=0) #TODO remove

  def __init__(self, name=None, worker_class=None, pipeline_id=None):
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

  def get_status(self, retries = 10):
    client = memcache.Client()
    key = str(self.pipeline_id) + "_" + str(self.id) + "_" + "status"
    while retries > 0:
      status = client.gets(key)
      if status is None: 
        """The status is uninitialized in memcache, 
          getting it from the database and
          updating its value in memcache
        """
        client.set(key, self.status, time = MEMCACHE_DEFAULT_EXPIRATION_TIME)
        return self.status
      if client.cas(key, status):
        return status
      retries -= 1

  def prepare_for_start(self, retries = 10):
    """
      Check the current status of the job and update for 'running'
    """
    client = memcache.Client()
    key = str(self.pipeline_id) + "_" + str(self.id) + "_" + "status"
    while retries > 0:
      status = client.gets(key)
      if status is None: 
        """The status is uninitialized in memcache, 
        getting it from the database and
        updating its value in memcache
        """
        if self.status not in ['idle', 'succeeded', 'failed']:
          client.set(key, self.status, time = MEMCACHE_DEFAULT_EXPIRATION_TIME)
          return False
        """The job is ready to start running"""
        client.set(key, 'waiting', time = MEMCACHE_DEFAULT_EXPIRATION_TIME)
        return True
      if client.cas(key, status):
        if status not in ['idle', 'succeeded', 'failed']:
          return False
        return True
      retries -= 1

  def get_ready(self):
    try:
      for param in self.params:
        _ = param.val  # NOQA
    except (InvalidExpression, TypeError) as e:
      from core.logging import logger
      logger.log_struct({
          'labels': {
              'pipeline_id': self.pipeline_id,
              'job_id': self.id,
              'worker_class': self.worker_class,
          },
          'log_level': 'ERROR',
          'message': 'Bad job param "%s": %s' % (param.label, e),
      })
      return False
    if self.prepare_for_start():  
      return True
    else:
      logger.log_struct({
          'labels': {
              'pipeline_id': self.pipeline_id,
              'job_id': self.id,
              'worker_class': self.worker_class,
          },
          'log_level': 'ERROR',
          'message': 'Memcache error - could not update the status of the job',
      })
      return False
  
  def _set_multi_memcache(self, mapping, time = MEMCACHE_DEFAULT_EXPIRATION_TIME, retries = 10):
    """
        Set multiple values in memcache, prefixed by the id of the pipeline
        and having a default expiration time of 24 hours
    """
    client = memcache.Client()
    while retries > 0:
      cached_mapping = client.gets(key)
      if cached_mapping is None: 
        client.set_multi(mapping, key_prefix = str(self.pipeline_id) + "_", time = time)
        return True
      if client.cas_multi(mapping, key_prefix = str(self.pipeline_id) + "_", time = time):
        return True
      retries -= 1

  def _set_memcache(self, key, value, time = MEMCACHE_DEFAULT_EXPIRATION_TIME, retries = 10):
    key = str(self.pipeline_id) + "_" + key
    client = memcache.Client()
    while retries > 0:
      cached_value = client.gets(key)
      if cached_value is None: 
        client.set(key, value, time = time)
        return True
      if client.cas(key, value, time = time):
        return True
      retries -= 1

  def _increase_value_memcache(self, key, db_value = None, time = MEMCACHE_DEFAULT_EXPIRATION_TIME, retries = 10):
    """
    params:
    db_value = default value from database in case the variable 
              has not been initialized in memcache
    """
    key = str(self.pipeline_id) + "_" + key
    client = memcache.Client()
    while retries > 0:
      cached_value = client.gets(key)
      if cached_value is None:
        db_value = db_value + 1 if db_value else 0
        client.set(key, db_value, time = time)
        return False
      if client.cas(key, cached_value + 1, time = time):
        return True
      retries -= 1

  def _decrease_value_memcache(self, key, db_value = None, time = MEMCACHE_DEFAULT_EXPIRATION_TIME, retries = 10):
    """
    params:
    db_value = default value from database in case the variable 
              has not been initialized in memcache
    """
    key = str(self.pipeline_id) + "_" + key
    client = memcache.Client()
    while retries > 0:
      cached_value = client.gets(key)
      if cached_value is None: 
        db_value = db_value - 1 if db_value else 0
        client.set(key, db_value, time = time)
        return False
      if client.cas(key, cached_value - 1, time = time):
        return True
      retries -= 1

  def _add_task_name_memcache(self, task_name, key = "list_of_tasks_enqueued", 
    time = MEMCACHE_DEFAULT_EXPIRATION_TIME, retries = 10):
    key = str(self.pipeline_id) + "_" + key
    client = memcache.Client()
    while retries > 0:
      cached_value = client.gets(key)
      if cached_value is None: 
        client.set(key, [task_name], time = time)
        return True
      if client.cas(key, cached_value + [task_name], time = time):
        return True
      retries -= 1

  def _delete_task_name_memcache(self, task_name, key = "list_of_tasks_enqueued", 
                                  time = MEMCACHE_DEFAULT_EXPIRATION_TIME, retries = 10):
    key = str(self.pipeline_id) + "_" + key
    client = memcache.Client()
    while retries > 0:
      cached_value = client.gets(key)
      if cached_value is None: 
        client.set(key, [], time = time)
        return True
      if client.cas(key, [task for task in cached_value if task != task_name], time = time):
        return True
      retries -= 1

  def _get_by_key_memcache(self, key):
    key = str(self.pipeline_id) + "_" + key
    client = memcache.Client()
    return client.get(key)

  def start(self):
    """
    TODO(dulacp): refactor this method, too complex branching logic
    """
    if self.get_status() != 'waiting':
      return False
    for start_condition in self.start_conditions:
      if start_condition.condition == 'success':
        if start_condition.preceding_job.get_status() != 'succeeded':
          if start_condition.preceding_job.get_status() == 'failed':
            self.set_failed_status()
            # TODO replace method with cancelling tasks method
            self._start_dependent_jobs()
          return False
      elif start_condition.condition == 'fail':
        if start_condition.preceding_job.get_status() != 'failed':
          if start_condition.preceding_job.get_status() == 'succeeded':
            self.set_failed_status()
            # TODO replace method with cancelling tasks method
            self._start_dependent_jobs()
          return False
      elif start_condition.condition == 'whatever':
        if start_condition.preceding_job.get_status() not in ['succeeded', 'failed']:
          return False
    self.run()
    return True

  def run(self):
    self.enqueued_workers_count = 0
    self.succeeded_workers_count = 0
    self.failed_workers_count = 0
    self._set_memcache(str(self.id) + "_status", 'running')
    worker_params = dict([(p.name, p.val) for p in self.params])
    self.enqueue(self.worker_class, worker_params)

  def stop(self):
    if self.status == 'waiting':
      self.update(status='failed', status_changed_at=datetime.now())
      return True
    elif self.status == 'running':
      self.update(status='stopping', status_changed_at=datetime.now())
      return True
    return False

  def enqueue(self, worker_class, worker_params, delay=0):
    if self.get_status() != 'running':
      return False
    task_name = '%s_%s_%s' % (self.pipeline.name, self.name, self.worker_class)
    escaped_task_name = re.sub(r'[^-_0-9a-zA-Z]', '-', task_name)
    unique_task_name = '%s_%s' % (escaped_task_name, str(uuid.uuid4()))
    self._add_task_name_memcache(unique_task_name)
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
    self.enqueued_workers_count += 1
    self._increase_value_memcache(str(self.id) + "_enqueued_tasks")
    self.save()
    return task

  @property
  def finished_workers_count(self):
    return self.succeeded_workers_count + self.failed_workers_count

  def _start_dependent_jobs(self):
    if self.dependent_jobs:
      for job in self.dependent_jobs:
        job.start()
    self.pipeline.job_finished()

  def set_failed_status(self):
    self._increase_value_memcache("failed_jobs")
    self._decrease_value_memcache("remaining_jobs", db_value = len(self.pipeline.jobs.all()))
    self._set_memcache(str(self.id) + "_status", 'failed')
    self.update(status='failed', status_changed_at=datetime.now())
    self.pipeline.status = 'failed'
    # TODO cancel all other jobs in the pipeline with the status 'failed'

  def set_succeeded_status(self):
    self._decrease_value_memcache("remaining_jobs", db_value = len(self.pipeline.jobs.all()))
    self._set_memcache(str(self.id) + "_status", 'succeeded')
    self.update(status='succeeded', status_changed_at=datetime.now())

  def worker_succeeded(self, task_name):
    self._delete_task_name_memcache(task_name)
    self._decrease_value_memcache(str(self.id) + "_enqueued_tasks", 
                                  db_value = self.enqueued_workers_count)
    self.succeeded_workers_count += 1
    if self._get_by_key_memcache(str(self.id) + "_enqueued_tasks") == 0:
      if self.get_status() != 'failed':
        self.set_succeeded_status()
      else:
        self.set_failed_status()
      # TODO remove after it is implemented in set_failed/success_status
      self._start_dependent_jobs()
    else:
      self.save()

  def worker_failed(self, task_name):
    self._delete_task_name_memcache(task_name)
    self._decrease_value_memcache(str(self.id) + "_enqueued_tasks")
    self.failed_workers_count += 1
    self.set_failed_status()
    if self._get_by_key_memcache(str(self.id) + "_enqueued_tasks") == 0:
      self._start_dependent_jobs()
    else:
      # TODO cancel other workers in the job
      self.save()

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

  _INLINER_REGEX = re.compile(r'{%.+?%}')

  def _expand_vars(self, value):
    names = {'True': True, 'False': False}
    if self.job_id is not None or self.pipeline_id is not None:
      for param in Param.where(pipeline_id=None, job_id=None).all():
        names[param.name] = param.val
    if self.job_id is not None:
      for param in self.job.pipeline.params:
        names[param.name] = param.val
    inliners = self._INLINER_REGEX.findall(value)
    for inliner in inliners:
      result = simple_eval(inliner[2:-2], functions=inline.functions,
                           names=names)
      value = value.replace(inliner, str(result))
    return value

  @property
  def val(self):
    if self.type == 'boolean':
      return self.value == '1'
    val = self._expand_vars(self.value)
    if self.type == 'number':
      return _parse_num(val)
    if self.type == 'string_list':
      return val.split('\n')
    if self.type == 'number_list':
      return [_parse_num(l) for l in val.split('\n') if l.strip()]
    return val

  @property
  def api_val(self):
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

  job = relationship("Job", foreign_keys=[job_id])
  preceding_job = relationship("Job", foreign_keys=[preceding_job_id])

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
        "id": int(value['preceding_job_id']),
        "condition": value['condition']
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
