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

"""Worker section."""


# TODO(aprikhodko): Move this blueprint to the jobs service.


from flask import Blueprint
from flask_restful import Resource, marshal_with, fields
from jobs import workers
from controller.extensions import api

blueprint = Blueprint('worker', __name__)

param_fields = {
    'name': fields.String,
    'label': fields.String,
    'default': fields.String,
    'required': fields.Boolean,
    'type': fields.String,
}


class WorkerList(Resource):
  """Shows a list of available workers"""

  def get(self):
    return workers.AVAILABLE, 200


class WorkerParams(Resource):
  """Shows a list of all params for selected worker class"""

  @marshal_with(param_fields)
  def get(self, worker_class):
    klass = getattr(workers, worker_class)
    keys = ['name', 'type', 'required', 'default', 'label']
    return [dict(zip(keys, param)) for param in klass.PARAMS]


api.add_resource(WorkerList, '/workers')
api.add_resource(WorkerParams, '/workers/<worker_class>/params')
