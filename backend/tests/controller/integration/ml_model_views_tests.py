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

import mock
from controller.models import MlModel, Pipeline, GeneralSetting
from controller.ml_model.bigquery import Variable, Parameter
from tests import controller_utils


class TestMlModelViews(controller_utils.ControllerAppTest):

  def test_empty_list(self):
    response = self.client.get('/api/ml-models')
    self.assertEqual(response.status_code, 200)

  def test_list_with_one_ml_model(self):
    MlModel.create(name='Test Model', type='LOGISTIC_REG', unique_id='CLIENT_ID', destination='GOOGLE_ANALYTICS_CUSTOM_EVENT')
    response = self.client.get('/api/ml-models')
    self.assertEqual(response.status_code, 200)

  def test_get_missing_ml_model(self):
    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_put_missing_ml_model(self):
    response = self.client.put('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_put_active_ml_model(self):
    model = MlModel.create(name='Test Model', type='LOGISTIC_REG', unique_id='CLIENT_ID', destination='GOOGLE_ANALYTICS_CUSTOM_EVENT')
    pipeline = Pipeline.create(ml_model_id=model.id)
    pipeline.status = Pipeline.STATUS.RUNNING
    pipeline.save()
    response = self.client.put('/api/ml-models/1')
    self.assertEqual(response.status_code, 422)

  def test_put_ml_model(self):
    self.post_test_model()

    request = {
      "name": "Test Model - Update",
      "bigquery_dataset": {
        "name": "test-dataset-update",
        "location": "UK"
      },
      "type": "BOOSTED_TREE_CLASSIFIER",
      "unique_id": "USER_ID",
      "uses_first_party_data": False,
      "hyper_parameters": [
        {"name": "L1_REG", "value": "2"},
        {"name": "L2_REG", "value": "4"},
        {"name": "BOOSTER_TYPE", "value": "GBTREE"},
        {"name": "MAX_ITERATIONS", "value": "12"},
        {"name": "SUBSAMPLE", "value": "0.4"},
        {"name": "TREE_METHOD", "value": "HIST"},
        {"name": "ENABLE_GLOBAL_EXPLAIN", "value": "false"},
        {"name": "NUM_PARALLEL_TREE", "value": "4"},
        {"name": "DATA_SPLIT_METHOD", "value": "AUTO_SPLIT"},
        {"name": "EARLY_STOP", "value": "true"}
      ],
      "features": [{
        "name": "enrollment",
        "source": "FIRST_PARTY"
      }],
      "label": {
          "name": "purchase",
          "source": "GOOGLE_ANALYTICS",
          "key": "value",
          "value_type": "int",
          "average_value": 123.45
      },
      "class_imbalance": 5,
      "timespans": [
        {"name": "training", "value": 14, "unit": "month"},
        {"name": "predictive", "value": 2, "unit": "month"}
      ],
      "destination": "GOOGLE_ADS_CONVERSION_EVENT"
    }

    response = self.client.put('/api/ml-models/1', json=request)
    ml_model = response.json
    self.assertEqual(ml_model['id'], 1)
    self.assertLen(ml_model['pipelines'], 2)
    for key, value in request.items():
      if type(value) is list:
        ml_model[key].sort(key = lambda c : c['name'])
        value.sort(key = lambda c : c['name'])
      self.assertEqual(ml_model[key], value)

    self.assertEqual(response.status_code, 200)

  def test_delete_missing_ml_model(self):
    response = self.client.delete('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_delete_active_ml_model(self):
    model = MlModel.create(name='Test Model', type='LOGISTIC_REG', unique_id='CLIENT_ID', destination='GOOGLE_ANALYTICS_CUSTOM_EVENT')
    pipeline = Pipeline.create(ml_model_id=model.id)
    pipeline.status = Pipeline.STATUS.RUNNING
    pipeline.save()
    response = self.client.delete('/api/ml-models/1')
    self.assertEqual(response.status_code, 422)

  def test_delete_ml_model(self):
    MlModel.create(name='Test Model', type='LOGISTIC_REG', unique_id='CLIENT_ID', destination='GOOGLE_ANALYTICS_CUSTOM_EVENT')

    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 200)

    response = self.client.delete('/api/ml-models/1')
    self.assertEqual(response.status_code, 204)

    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_create_ml_model(self):
    request, response = self.post_test_model()
    ml_model = response.json
    self.assertEqual(ml_model['id'], 1)
    self.assertLen(ml_model['pipelines'], 2)
    for key, value in request.items():
      if type(value) is list:
        ml_model[key].sort(key = lambda c : c['name'])
        value.sort(key = lambda c : c['name'])
      self.assertEqual(ml_model[key], value)

    self.assertEqual(response.status_code, 201)

  @mock.patch('controller.models.MlModel.save_relations')
  def test_error_during_create_ml_model_causes_rollback(self, mock: mock.Mock):
    mock.side_effect = Exception('oops.')

    with self.assertRaises(Exception):
      self.post_test_model()

    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_retrieve_ml_model(self):
    model = MlModel.create(name='Test Model', type='LOGISTIC_REG', unique_id='CLIENT_ID', destination='GOOGLE_ANALYTICS_CUSTOM_EVENT')
    Pipeline.create(ml_model_id=model.id)
    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 200)

  def test_retrieve_variables_without_dataset(self):
    response = self.client.get('/api/ml-models/variables')
    self.assertEqual(response.status_code, 400)

  @mock.patch('controller.ml_model.bigquery.CustomClient')
  def test_retrieve_variables_with_dataset(self, client_mock: mock.Mock):
    dataset = {'dataset_name': 'test-dataset', 'dataset_location': 'US'}
    GeneralSetting.where(name='google_analytics_4_bigquery_dataset').first().update(value='test-ga4-dataset')

    # required due to uncertainty around how to do actual integration test with big query locally
    variables: list[Variable] = []
    variable = Variable('test-name', 'GOOGLE_ANALYTICS', 1, [])
    variable.parameters.append(Parameter('test-key', 'test-value-type'))
    variables.append(variable)
    client_mock.return_value.get_analytics_variables.return_value = variables

    response = self.client.get('/api/ml-models/variables', query_string=dataset)
    self.assertEqual(response.status_code, 200)

  @mock.patch('controller.ml_model.bigquery.CustomClient')
  def test_retrieve_variables_with_dataset_events_not_found(self, client_mock: mock.Mock):
    dataset = {'dataset_name': 'test-dataset', 'dataset_location': 'US'}
    GeneralSetting.where(name='google_analytics_4_bigquery_dataset').first().update(value='test-ga4-dataset')

    # required due to uncertainty around how to do actual integration test with big query locally
    variables: list[Variable] = []
    client_mock.return_value.get_analytics_variables.return_value = variables

    response = self.client.get('/api/ml-models/variables', query_string=dataset)
    self.assertEqual(response.status_code, 400)


  def post_test_model(self):
    request = {
      "name": "Test Model",
      "bigquery_dataset": {
        "name": "test-dataset",
        "location": "US"
      },
      "type": "BOOSTED_TREE_REGRESSOR",
      "unique_id": "CLIENT_ID",
      "uses_first_party_data": False,
      "hyper_parameters": [
        {"name": "L1_REG", "value": "1"},
        {"name": "L2_REG", "value": "1"},
        {"name": "BOOSTER_TYPE", "value": "GBTREE"},
        {"name": "MAX_ITERATIONS", "value": "50"},
        {"name": "SUBSAMPLE", "value": "0.8"},
        {"name": "TREE_METHOD", "value": "HIST"},
        {"name": "ENABLE_GLOBAL_EXPLAIN", "value": "true"},
        {"name": "NUM_PARALLEL_TREE", "value": "2"},
        {"name": "DATA_SPLIT_METHOD", "value": "AUTO_SPLIT"},
        {"name": "EARLY_STOP", "value": "false"}
      ],
      "features": [{
        "name": "click",
        "source": "GOOGLE_ANALYTICS"
      }],
      "label": {
        "name": "purchase",
        "key": "",
        "value_type": "",
        "source": "FIRST_PARTY",
        "average_value": 0.0
      },
      "class_imbalance": 7,
      "timespans": [
        {"name": "training", "value": 20, "unit": "month"},
        {"name": "predictive", "value": 1, "unit": "month"}
      ],
      "destination": "GOOGLE_ANALYTICS_CUSTOM_EVENT"
    }

    response = self.client.post('/api/ml-models', json=request)
    return (request, response)
