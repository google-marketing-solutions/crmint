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


import json
from flask import Blueprint
from flask import request
from flask_restful import Resource, reqparse
from core.models import Job
from core import workers
from jbackend.extensions import api


blueprint = Blueprint('task', __name__)
parser = reqparse.RequestParser()
parser.add_argument('job_id')
parser.add_argument('worker_class')
parser.add_argument('worker_params')


class Task(Resource):
  """Lets you POST to add new task."""

  def post(self):
    """
    NB: you want retrieve the task name with this snippet

        task_name = request.headers.get('X-AppEngine-TaskName')[11:]

    """
    retries = int(request.headers.get('X-AppEngine-TaskExecutionCount'))
    args = parser.parse_args()
    job = Job.find(args['job_id'])
    worker_class = getattr(workers, args['worker_class'])
    worker_params = json.loads(args['worker_params'])
    worker = worker_class(worker_params, job.pipeline_id, job.id)
    if retries >= worker_class.MAX_ATTEMPTS:
      worker.log_error('Execution canceled after %i failed attempts', retries)
      job.worker_failed()
    elif job.status == 'stopping':
      worker.log_warn('Execution canceled as parent job is going to stop')
      job.worker_failed()
    else:
      try:
        # NB: Calls to execute() return an generator of workers to enqueue.
        worker_to_enqueue_gen = worker.execute()
        for worker_to_enqueue in worker_to_enqueue_gen:
          worker_class_name, worker_params, delay = worker_to_enqueue
          job.enqueue(worker_class_name, worker_params, delay)
      except workers.WorkerException as e:
        worker.log_error('Execution failed: %s: %s', e.__class__.__name__, e)
        job.worker_failed()
      except Exception as e:
        worker.log_error('Unexpected error: %s: %s', e.__class__.__name__, e)
        raise e
      else:
        job.worker_succeeded()
    return 'OK', 200


api.add_resource(Task, '/task')
