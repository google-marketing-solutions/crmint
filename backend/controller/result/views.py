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

import flask
from flask_restful import Api
from flask_restful import Resource

from common import message
from common import result
from controller import models

blueprint = flask.Blueprint('result', __name__)
api = Api(blueprint)


class ResultResource(Resource):
  """Processes PubSub POST requests with task results."""

  def post(self):
    try:
      res = result.Result.from_request(flask.request)
    except message.BadRequestError as e:
      return e.message, e.code
    if res.success:
      job = models.Job.find(res.job_id)
      for worker_enqueue_agrs in res.workers_to_enqueue:
        job.enqueue(*worker_enqueue_agrs)
      job.task_succeeded(res.task_name)
    else:
      job = models.Job.find(res.job_id)
      job.task_failed(res.task_name)
    return 'OK', 200


api.add_resource(ResultResource, '/push/task-finished')
