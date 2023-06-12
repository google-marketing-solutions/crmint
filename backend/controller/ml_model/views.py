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

"""MlModel views."""

import os
import json
from typing import Any

import flask
from flask_restful import abort
from flask_restful import Api
from flask_restful import fields
from flask_restful import marshal_with
from flask_restful import reqparse
from flask_restful import Resource

from common import insight
from controller.ml_model import bigquery
from controller.ml_model import compiler
from controller import models

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

blueprint = flask.Blueprint('ml_model', __name__)
api = Api(blueprint)

parser = reqparse.RequestParser()
parser.add_argument('name', type=str, required=False)
parser.add_argument('bigquery_dataset', type=dict, required=False)
parser.add_argument('type', type=str, required=False)
parser.add_argument('unique_id', type=str, required=False)
parser.add_argument('uses_first_party_data', type=bool, required=False)
parser.add_argument(
    'hyper_parameters', type=list, location='json', required=False
)
parser.add_argument('features', type=list, location='json', required=False)
parser.add_argument('label', type=dict, required=False)
parser.add_argument('conversion_rate_segments', type=int, required=False)
parser.add_argument('class_imbalance', type=int, required=False)
parser.add_argument('timespans', type=list, location='json', required=False)
parser.add_argument('output', type=dict, required=False)

bigquery_dataset_structure = fields.Nested(
    {'name': fields.String, 'location': fields.String}
)

hyper_parameters_structure = fields.List(
    fields.Nested({'name': fields.String, 'value': fields.String})
)

features_structure = fields.List(
    fields.Nested({'name': fields.String, 'source': fields.String})
)

label_structure = fields.Nested({
    'name': fields.String,
    'source': fields.String,
    'key': fields.String,
    'value_type': fields.String,
    'average_value': fields.Float,
})

timespans_structure = fields.List(
    fields.Nested(
        {'name': fields.String, 'value': fields.Integer, 'unit': fields.String}
    )
)

output_structure = fields.Nested({
    'destination': fields.String,
    'parameters': fields.Nested({
        'customer_id': fields.String,
        'conversion_action_id': fields.String
    })
})

pipelines_structure = fields.List(
    fields.Nested({
        'id': fields.Integer,
        'name': fields.String,
        'status': fields.String,
        'updated_at': fields.String,
        'schedules': fields.List(
            fields.Nested({
                'cron': fields.String,
            })
        ),
        'jobs': fields.List(
            fields.Nested({
                'name': fields.String,
                'params': fields.List(
                    fields.Nested({
                        'name': fields.String,
                        'value': fields.String,
                    })
                ),
            })
        ),
    })
)

ml_model_structure = {
    'id': fields.Integer,
    'name': fields.String,
    'bigquery_dataset': bigquery_dataset_structure,
    'type': fields.String,
    'unique_id': fields.String,
    'uses_first_party_data': fields.Boolean,
    'hyper_parameters': hyper_parameters_structure,
    'features': features_structure,
    'label': label_structure,
    'conversion_rate_segments': fields.Integer,
    'class_imbalance': fields.Integer,
    'timespans': timespans_structure,
    'output': output_structure,
    'pipelines': pipelines_structure,
    'updated_at': fields.String
}


class MlModelSingle(Resource):
  """Shows a single ml model item and lets you delete a ml model item."""

  @marshal_with(ml_model_structure)
  def get(self, id):  # pylint: disable=redefined-builtin
    tracker = insight.GAProvider()
    tracker.track_event(category='ml-models', action='get')

    ml_model = models.MlModel.find(id)
    abort_when_not_found(ml_model)
    return ml_model

  @marshal_with(ml_model_structure)
  def delete(self, id):  # pylint: disable=redefined-builtin
    ml_model = models.MlModel.find(id)

    abort_when_not_found(ml_model)
    abort_when_pipeline_active(ml_model)

    ml_model.destroy()

    tracker = insight.GAProvider()
    tracker.track_event(category='ml-models', action='delete')

    return {}, 204

  @marshal_with(ml_model_structure)
  def put(self, id):  # pylint: disable=redefined-builtin
    ml_model = models.MlModel.find(id)

    abort_when_not_found(ml_model)
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

    ml_models = models.MlModel.all()
    return ml_models

  @marshal_with(ml_model_structure)
  def post(self):
    tracker = insight.GAProvider()
    args = parser.parse_args()

    ml_model = models.MlModel(name=args['name'])
    try:
      ml_model.assign_attributes(args)
      ml_model.save()
      ml_model.save_relations(args)

      # Automatically build and assign training pipeline upon ml model creation.
      pipelines = build_pipelines(ml_model)
      ml_model.save_relations({'pipelines': pipelines})
    except:
      # Ensures that, in the event of an error, a half-implemented
      # ml model isn't created.
      ml_model.destroy()
      raise

    tracker.track_event(category='ml-models', action='create')

    return ml_model, 201


variables_parser = reqparse.RequestParser()
variables_parser.add_argument('dataset', type=str, required=True)
variables_parser.add_argument('timespans', type=str, required=True)

ml_variable_structure = {
    'name': fields.String,
    'count': fields.Integer,
    'source': fields.String,
    'parameters': fields.List(
        fields.Nested({
            'key': fields.String,
            'value_type': fields.String
        })
    )
}


class MlModelVariables(Resource):
  """Shows a list of all GA4 events.

  We return also counts as well as first party data columns
  and types that can be used to pick features and label for the model.
  """

  @marshal_with(ml_variable_structure)
  def get(self):
    tracker = insight.GAProvider()
    tracker.track_event(category='ml-models', action='variables')

    args = variables_parser.parse_args()
    dataset = json.loads(args['dataset'])
    timespan = compiler.Timespan(json.loads(args['timespans']))

    bigquery_client = bigquery.CustomClient(dataset['location'])
    variables = []

    ga4_dataset = setting('google_analytics_4_bigquery_dataset')

    # Timebox the variables/events to the training dataset timespan.
    analytics_variables = bigquery_client.get_analytics_variables(
        ga4_dataset, timespan.training_start, timespan.training_end)
    if not analytics_variables:
      abort(
          400,
          message=(
              'GA4 BigQuery Dataset does not include expected events tables.'
              ' Check configuration in Settings tab and try again.'
          ),
      )
    variables.extend(analytics_variables)

    first_party_columns = bigquery_client.get_first_party_variables(
        dataset['name']
    )
    if first_party_columns:
      variables.extend(first_party_columns)

    return variables


def abort_when_not_found(ml_model: models.MlModel):
  """Abort with an appropriate error if the model provided does not exist.

  Args:
    ml_model: The model to check.

  Raises:
    HTTPException: If the ml model id provided in the request was not found.
  """
  if ml_model is None:
    abort(404, message=f'MlModel {id} doesn\'t exist')


def abort_when_pipeline_active(ml_model: models.MlModel):
  """Abort with an appropriate error if the pipeline is active.

  Args:
    ml_model: The model to check.

  Raises:
    HTTPException: if the pipeline is considered "blocked".
  """
  for pipeline in ml_model.pipelines:
    if pipeline.is_blocked():
      abort(422, message='Removing or editing of ml model with '
                         'active pipeline is unavailable')


def setting(name: str) -> str:
  """Helper for getting general settings by name if they exist.

  Args:
    name: The name of the setting to return a value for.

  Returns:
    The value of the setting.
  """
  s = models.GeneralSetting.where(name=name).first()
  return s.value if s else ''


def build_pipelines(ml_model: models.MlModel) -> list[dict[str, Any]]:
  """Builds training and predictive pipelines.

  Args:
    ml_model: The ml model configuration necessary to build the BQML and pipelines.

  Returns:
    The newly built training and predictive pipeline objects.
  """
  c = compiler.Compiler(
    project_id=project_id,
    ga4_dataset=setting('google_analytics_4_bigquery_dataset'),
    ga4_measurement_id=setting('google_analytics_4_measurement_id'),
    ga4_api_secret=setting('google_analytics_4_api_secret'),
    ml_model=ml_model
  )

  training_pipeline = c.build_training_pipeline()
  predictive_pipeline = c.build_predictive_pipeline()

  return [training_pipeline, predictive_pipeline]


api.add_resource(MlModelList, '/ml-models')
api.add_resource(MlModelSingle, '/ml-models/<id>')
api.add_resource(MlModelVariables, '/ml-models/variables')
