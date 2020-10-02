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

"""Task results handler."""

from flask import Blueprint, request
from flask_restful import Resource
from common.message import BadRequestError
from common.result import Result
from controller.models import Job
from controller.extensions import api


blueprint = Blueprint('result', __name__)


class ResultResource(Resource):
  """Processes PubSub POST requests with task results."""

  def post(self):
    try:
      result = Result.from_request(request)
    except BadRequestError as e:
      return e.message, e.code
    if result.success:
      job = Job.find(result.job_id)
      for worker_enqueue_agrs in result.workers_to_enqueue:
        job.enqueue(*worker_enqueue_agrs)
      job.task_succeeded(result.task_name)
    else:
      job = Job.find(result.job_id)
      job.task_failed(result.task_name)
    return 'OK', 200


api.add_resource(ResultResource, '/push/task-finished')
