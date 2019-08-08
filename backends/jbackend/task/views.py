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

"""Task handler."""

import logging
import json

from google.appengine.api import urlfetch

from flask import Blueprint
from flask import request
from flask_restful import Resource, reqparse

from core import workers
from core.models import Job, GeneralSetting
from jbackend.extensions import api

logger = logging.getLogger(__name__)

blueprint = Blueprint('task', __name__)
parser = reqparse.RequestParser()
parser.add_argument('job_id')
parser.add_argument('worker_class')
parser.add_argument('worker_params')
parser.add_argument('task_name')


class Task(Resource):
  """Lets you POST to add new task."""

  def post(self):
    """
    NB: you want retrieve the task name with this snippet

        task_name = request.headers.get('X-AppEngine-TaskName')[11:]

    """
    urlfetch.set_default_fetch_deadline(300)
    retries = int(request.headers.get('X-AppEngine-TaskExecutionCount'))
    args = parser.parse_args()
    logger.debug(args)
    task_name = args['task_name']
    job = Job.find(args['job_id'])
    worker_class = getattr(workers, args['worker_class'])
    worker_params = json.loads(args['worker_params'])

    for setting in worker_class.GLOBAL_SETTINGS:
        worker_params[setting] = GeneralSetting.where(name=setting).first().value

    worker = worker_class(worker_params, job.pipeline_id, job.id)
    if retries >= worker_class.MAX_ATTEMPTS:
      worker.log_error('Execution canceled after %i failed attempts', retries)
      job.task_failed(task_name)
    elif job.status == 'stopping':
      worker.log_warn('Execution canceled as parent job is going to stop')
      job.task_failed(task_name)
    else:
      try:
        workers_to_enqueue = worker.execute()
      except workers.WorkerException as e:
        worker.log_error('Execution failed: %s: %s', e.__class__.__name__, e)
        job.task_failed(task_name)
      except Exception as e:
        worker.log_error('Unexpected error: %s: %s', e.__class__.__name__, e)
        raise e
      else:
        for worker_class_name, worker_params, delay in workers_to_enqueue:
          job.enqueue(worker_class_name, worker_params, delay)
        job.task_succeeded(task_name)
    return 'OK', 200


api.add_resource(Task, '/task')
