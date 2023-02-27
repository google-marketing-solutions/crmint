# Copyright 2023 Google Inc
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

"""MlModel section."""

import flask
import os

from flask_restful import abort
from flask_restful import Api
from flask_restful import fields
from flask_restful import marshal_with
from flask_restful import reqparse
from flask_restful import Resource

from common import insight
from controller.models import MlModel, GeneralSetting

from controller.ml_model import bigquery
from controller.ml_model.templates import compiler

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

blueprint = flask.Blueprint('ml_model', __name__)
api = Api(blueprint)

parser = reqparse.RequestParser()
parser.add_argument('name', type=str, required=False)
parser.add_argument('bigquery_dataset', type=dict, required=False)
parser.add_argument('type', type=str, required=False)
parser.add_argument('unique_id', type=str, required=False)
parser.add_argument('uses_first_party_data', type=bool, required=False)
parser.add_argument('hyper_parameters', type=list, location='json', required=False)
parser.add_argument('features', type=list, location='json', required=False)
parser.add_argument('label', type=dict, required=False)
parser.add_argument('skew_factor', type=int, required=False)
parser.add_argument('timespans', type=list, location='json', required=False)

ml_model_structure = {
  'id': fields.Integer,
  'name': fields.String,
  'bigquery_dataset': fields.Nested({
    'name': fields.String,
    'location': fields.String
  }),
  'type': fields.String,
  'unique_id': fields.String,
  'uses_first_party_data': fields.Boolean,
  'hyper_parameters': fields.List(fields.Nested({
    'name': fields.String,
    'value': fields.String
  })),
  'features': fields.List(fields.Nested({
    'name': fields.String,
    'source': fields.String
  })),
  'label': fields.Nested({
    'name': fields.String,
    'source': fields.String,
    'key': fields.String,
    'value_type': fields.String
  }),
  'skew_factor': fields.Integer,
  'timespans': fields.List(fields.Nested({
    'name': fields.String,
    'value': fields.Integer,
    'unit': fields.String
  })),
  'pipelines': fields.List(fields.Nested({
    'id': fields.Integer,
    'name': fields.String,
    'status': fields.String,
    'updated_at': fields.String,
    'schedules': fields.List(fields.Nested({
      'cron': fields.String
    })),
    'jobs': fields.List(fields.Nested({
      'name': fields.String,
      'params': fields.List(fields.Nested({
        'name': fields.String,
        'value': fields.String
      }))
    }))
  })),
  'updated_at': fields.String
}

ml_variables_structure = fields.List(fields.Nested({
  'name': fields.String,
  'count': fields.Integer,
  'parameters': fields.List(fields.Nested({
    'key': fields.String,
    'value_type': fields.String
  }))
}))

bigquery_client = bigquery.Client()

class MlModelSingle(Resource):
  """Shows a single ml model item and lets you delete a ml model item."""

  @marshal_with(ml_model_structure)
  def get(self, id):
    tracker = insight.GAProvider()
    tracker.track_event(category='ml-models', action='get')

    ml_model = MlModel.find(id)
    abort_when_not_found(ml_model, id)
    return ml_model

  @marshal_with(ml_model_structure)
  def delete(self, id):
    ml_model = MlModel.find(id)

    abort_when_not_found(ml_model, id)
    abort_when_pipeline_active(ml_model)

    ml_model.destroy()

    tracker = insight.GAProvider()
    tracker.track_event(category='ml-models', action='delete')

    return {}, 204

  @marshal_with(ml_model_structure)
  def put(self, id):
    ml_model = MlModel.find(id)

    abort_when_not_found(ml_model, id)
    abort_when_pipeline_active(ml_model)

    args = parser.parse_args()
    ml_model.assign_attributes(args)
    ml_model.save()
    ml_model.save_relations(args)

    pipelines = build_pipelines(ml_model)
    ml_model.save_relations({'pipelines': pipelines})

    tracker = insight.GAProvider()
    tracker.track_event(category='ml-models', action='update')

    return ml_model, 200


class MlModelList(Resource):
  """Shows a list of all ml models, and lets you POST to add new ml models."""

  @marshal_with(ml_model_structure)
  def get(self):
    tracker = insight.GAProvider()
    tracker.track_event(category='ml-models', action='list')

    ml_models = MlModel.all()
    return ml_models

  @marshal_with(ml_model_structure)
  def post(self):
    tracker = insight.GAProvider()
    args = parser.parse_args()

    ml_model = MlModel(name=args['name'])
    try:
      ml_model.assign_attributes(args)
      ml_model.save()
      ml_model.save_relations(args)

      # automatically build and assign training pipeline upon ml model creation.
      pipelines = build_pipelines(ml_model)
      ml_model.save_relations({'pipelines': pipelines})
    except:
      # ensuring that, in the event of an error, a half-implemented ml model isn't created.
      ml_model.destroy()
      raise

    tracker.track_event(category='ml-models', action='create')

    return ml_model, 201

class MlModelVariables(Resource):
  """Shows a list of all GA4 events and their counts as well as first party data columns
     and types that can be used to pick features and label for the model."""

  @marshal_with(ml_variables_structure)
  def get(self):
    tracker = insight.GAProvider()
    tracker.track_event(category='ml-models', action='variables')

    args = parser.parse_args()

    if not args['bigquery_dataset']:
      abort(400, message='Required parameter missing "bigquery_dataset".')

    variables = []

    dataset = setting('google_analytics_4_bigquery_dataset')
    variables.extend(bigquery_client.get_analytics_variables(dataset))

    first_party_columns = bigquery_client.get_first_party_variables(args['bigquery_dataset']['name'])
    if len(first_party_columns) > 0:
      variables.extend(first_party_columns)

    return variables


# helper functions for commonly used behavior
def abort_when_not_found(ml_model, id):
  if ml_model is None:
    abort(404, message="MlModel {} doesn't exist".format(id))

def abort_when_pipeline_active(ml_model):
    for pipeline in ml_model.pipelines:
      if pipeline.is_blocked():
        abort(422, message='Removing or editing of ml model with active pipeline is unavailable')

def setting(name: str) -> str:
  setting = GeneralSetting.where(name=name).first()
  return setting.value if setting else ''

def build_pipelines(ml_model) -> list[dict]:
  ga4_dataset = setting('google_analytics_4_bigquery_dataset')
  ga4_measurement_id = setting('google_analytics_4_measurement_id')
  ga4_api_secret = setting('google_analytics_4_api_secret')

  training_pipeline = compiler.build_training_pipeline(ml_model, project_id, ga4_dataset)
  predictive_pipeline = compiler.build_predictive_pipeline(ml_model, project_id, ga4_dataset, ga4_measurement_id, ga4_api_secret)

  return [training_pipeline, predictive_pipeline]


api.add_resource(MlModelList, '/ml-models')
api.add_resource(MlModelSingle, '/ml-models/<id>')
api.add_resource(MlModelVariables, '/ml-models/variables')