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

"""Stage section."""

from flask import Blueprint
from flask_restful import abort
from flask_restful import Api
from flask_restful import fields
from flask_restful import marshal_with
from flask_restful import reqparse
from flask_restful import Resource

from controller import models

blueprint = Blueprint('stage', __name__)
api = Api(blueprint)

parser = reqparse.RequestParser()
parser.add_argument('sid')

stage_fields = {
    'id': fields.Integer,
    'sid': fields.String
}


def abort_if_stage_doesnt_exist(stage, stage_id):
  if stage is None:
    abort(404, message="Stage {} doesn't exist".format(stage_id))


# TODO(dulacp): Removes these endpoints that are not used anymore.
class StageSingle(Resource):
  """Shows a single stage item and lets you delete a stage item."""

  @marshal_with(stage_fields)
  def get(self, stage_id):
    stage = models.Stage.find(stage_id)
    abort_if_stage_doesnt_exist(stage, stage_id)
    return stage

  @marshal_with(stage_fields)
  def delete(self, stage_id):
    stage = models.Stage.find(stage_id)

    abort_if_stage_doesnt_exist(stage, stage_id)

    stage.delete()
    return {}, 204

  @marshal_with(stage_fields)
  def put(self, stage_id):
    stage = models.Stage.find(stage_id)
    abort_if_stage_doesnt_exist(stage, stage_id)

    args = parser.parse_args()

    stage.assign_attributes(args)
    stage.save()
    return stage, 200


class StageList(Resource):
  """Shows a list of all stages, and lets you POST to add new stages."""

  @marshal_with(stage_fields)
  def get(self):
    stages = models.Stage.all()
    return stages

  @marshal_with(stage_fields)
  def post(self):
    args = parser.parse_args()
    print('args: ' + args.__str__())
    stage = models.Stage()
    stage.assign_attributes(args)
    stage.save()
    return stage, 201


api.add_resource(StageList, '/stages')
api.add_resource(StageSingle, '/stages/<stage_id>')
