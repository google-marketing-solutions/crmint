# Copyright 2023 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the 'License");
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

from unittest import mock

from controller import ml_model
from controller import models
from tests import controller_utils


class TestMlModelViews(controller_utils.ControllerAppTest):

  def test_empty_list(self):
    response = self.client.get('/api/ml-models')
    self.assertEqual(response.status_code, 200)

  def test_list_with_one_ml_model(self):
    models.MlModel.create(name='Test Model',
                          type='LOGISTIC_REG',
                          unique_id='CLIENT_ID')
    response = self.client.get('/api/ml-models')
    self.assertEqual(response.status_code, 200)

  def test_get_missing_ml_model(self):
    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_put_missing_ml_model(self):
    response = self.client.put('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_put_active_ml_model(self):
    model = models.MlModel.create(name='Test Model',
                                  type='LOGISTIC_REG',
                                  unique_id='CLIENT_ID')
    pipeline = models.Pipeline.create(ml_model_id=model.id)
    pipeline.status = models.Pipeline.STATUS.RUNNING
    pipeline.save()
    response = self.client.put('/api/ml-models/1')
    self.assertEqual(response.status_code, 422)

  def test_put_ml_model(self):
    self.post_test_model()

    request = {
        'name': 'Test Model - Update',
        'input': {
            'source': 'GOOGLE_ANALYTICS',
            'parameters': {
              'first_party_dataset': 'FP_DATASET',
              'first_party_table': 'FP_DATA_TABLE'
            }
        },
        'bigquery_dataset': {
            'name': 'test-dataset-update',
            'location': 'UK'
        },
        'type': 'BOOSTED_TREE_CLASSIFIER',
        'unique_id': 'USER_ID',
        'hyper_parameters': [
            {'name': 'L1_REG', 'value': '2'},
            {'name': 'L2_REG', 'value': '4'},
            {'name': 'BOOSTER_TYPE', 'value': 'GBTREE'},
            {'name': 'MAX_ITERATIONS', 'value': '12'},
            {'name': 'SUBSAMPLE', 'value': '0.4'},
            {'name': 'TREE_METHOD', 'value': 'HIST'},
            {'name': 'ENABLE_GLOBAL_EXPLAIN', 'value': 'false'},
            {'name': 'NUM_PARALLEL_TREE', 'value': '4'},
            {'name': 'DATA_SPLIT_METHOD', 'value': 'AUTO_SPLIT'},
            {'name': 'EARLY_STOP', 'value': 'true'}
        ],
        'variables': [
          {
            'name': 'first_purchase',
            'source': 'FIRST_PARTY',
            'role': 'FIRST_VALUE',
            'key': None,
            'value_type': None
          },
          {
            'name': 'first_purchase_date',
            'source': 'FIRST_PARTY',
            'role': 'TRIGGER_DATE',
            'key': None,
            'value_type': None
          },
          {
            'name': 'enrollment',
            'source': 'FIRST_PARTY',
            'role': 'FEATURE',
            'key': None,
            'value_type': None
          },
          {
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'role': 'LABEL',
            'key': 'value',
            'value_type': 'int'
          }
        ],
        'conversion_rate_segments': 10,
        'class_imbalance': 5,
        'timespans': [
            {'name': 'training', 'value': 14, 'unit': 'month'},
            {'name': 'predictive', 'value': 2, 'unit': 'month'}
        ],
        'output': {
            'destination': 'GOOGLE_ADS_OFFLINE_CONVERSION',
            'parameters': {
                'customer_id': '1234567890',
                'conversion_action_id': '0987654321',
                'average_conversion_value': 1234.5
            }
        }
    }

    response = self.client.put('/api/ml-models/1', json=request)
    data = response.json
    self.assertEqual(data['id'], 1)
    self.assertLen(data['pipelines'], 2)
    for key, value in request.items():
      if isinstance(value, list):
        data[key].sort(key=lambda c: c['name'])
        value.sort(key=lambda c: c['name'])
      self.assertEqual(data[key], value)

    self.assertEqual(response.status_code, 200)

  def test_delete_missing_ml_model(self):
    response = self.client.delete('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_delete_active_ml_model(self):
    model = models.MlModel.create(name='Test Model',
                                  type='LOGISTIC_REG',
                                  unique_id='CLIENT_ID')
    pipeline = models.Pipeline.create(ml_model_id=model.id)
    pipeline.status = models.Pipeline.STATUS.RUNNING
    pipeline.save()
    response = self.client.delete('/api/ml-models/1')
    self.assertEqual(response.status_code, 422)

  def test_delete_ml_model(self):
    models.MlModel.create(name='Test Model',
                          type='LOGISTIC_REG',
                          unique_id='CLIENT_ID')

    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 200)

    response = self.client.delete('/api/ml-models/1')
    self.assertEqual(response.status_code, 204)

    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_create_ml_model(self):
    request, response = self.post_test_model()
    test_model = response.json
    self.assertEqual(test_model['id'], 1)
    self.assertLen(test_model['pipelines'], 2)
    for key, value in request.items():
      if isinstance(value, list):
        test_model[key].sort(key=lambda c: c['name'])
        value.sort(key=lambda c: c['name'])
      self.assertEqual(test_model[key], value)

    self.assertEqual(response.status_code, 201)

  @mock.patch.object(models.MlModel, 'save_relations')
  def test_error_during_create_ml_model_causes_rollback(
      self, save_patch: mock.Mock
    ):
    save_patch.side_effect = ValueError('oops.')

    with self.assertRaises(ValueError):
      self.post_test_model()

    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 404)

  def test_retrieve_ml_model(self):
    model = models.MlModel.create(name='Test Model',
                                  type='LOGISTIC_REG',
                                  unique_id='CLIENT_ID')
    models.Pipeline.create(ml_model_id=model.id)
    response = self.client.get('/api/ml-models/1')
    self.assertEqual(response.status_code, 200)

  def test_retrieve_variables_without_required_fields(self):
    response = self.client.get('/api/ml-models/variables')
    self.assertEqual(response.status_code, 400)

  @mock.patch.object(ml_model.bigquery, 'CustomClient')
  def test_retrieve_variables_with_required_fields_google_analytics(
    self, client_mock: mock.Mock):
    request = {
        'input': '{\"source\":\"GOOGLE_ANALYTICS\",\"parameters\":{}}',
        'dataset': '{\"name\":\"test-dataset\",\"location\":\"US\"}',
        'timespans': '[{\"name\":\"training\",\"value\":90},'
                     '{\"name\":\"predictive\",\"value\":30}]',
    }
    models.GeneralSetting.where(
        name='google_analytics_4_bigquery_dataset'
    ).first().update(value='test-ga4-dataset')

    # Required due to uncertainty around how to do actual integration
    # test with big query locally.
    variables: list[ml_model.bigquery.Variable] = []
    variable = ml_model.bigquery.Variable(
        'test-name', 'GOOGLE_ANALYTICS', 1, [])
    variable.parameters.append(
        ml_model.bigquery.Parameter('test-key', 'test-value-type'))
    variables.append(variable)
    client_mock.return_value.get_analytics_variables.return_value = variables

    response = self.client.get('/api/ml-models/variables', query_string=request)
    self.assertEqual(response.status_code, 200)

  @mock.patch.object(ml_model.bigquery, 'CustomClient')
  def test_retrieve_variables_with_required_fields_first_party(
    self, client_mock: mock.Mock):
    request = {
        'input': '{\"source\":\"GOOGLE_ANALYTICS_AND_FIRST_PARTY\",\"parameters\":'
                 '{\"first_party_dataset\":\"1p_dataset\",'
                 '\"first_party_table\":\"1p_table\"}}',
        'dataset': '{\"name\":\"test-dataset\",\"location\":\"US\"}',
        'timespans': '[{\"name\":\"training\",\"value\":90},'
                     '{\"name\":\"predictive\",\"value\":30}]',
    }
    models.GeneralSetting.where(
        name='google_analytics_4_bigquery_dataset'
    ).first().update(value='test-ga4-dataset')

    # Required due to uncertainty around how to do actual integration
    # test with big query locally.
    variables: list[ml_model.bigquery.Variable] = []
    variable = ml_model.bigquery.Variable(
        'test-name', 'GOOGLE_ANALYTICS', 100, [])
    variable.parameters.append(
        ml_model.bigquery.Parameter('test-key', 'test-value-type'))
    variables.append(variable)
    client_mock.return_value.get_analytics_variables.return_value = variables

    variables: list[ml_model.bigquery.Variable] = []
    variable = ml_model.bigquery.Variable(
        'test-name', 'FIRST_PARTY', 0, [])
    variable.parameters.append(
        ml_model.bigquery.Parameter('test-key', 'test-value-type'))
    variables.append(variable)
    client_mock.return_value.get_first_party_variables.return_value = variables

    response = self.client.get('/api/ml-models/variables', query_string=request)
    self.assertEqual(response.status_code, 200)

  @mock.patch.object(ml_model.bigquery, 'CustomClient')
  def test_retrieve_variables_with_dataset_events_not_found(
      self, client_mock: mock.Mock):
    request = {
        'input': '{\"source\": \"GOOGLE_ANALYTICS\", \"parameters\": {}}',
        'dataset': '{\"name\": \"test-dataset\", \"location\": \"US\"}',
        'timespans': '[{\"name\": \"training\", \"value\": 90},'
                     '{\"name\": \"predictive\", \"value\": 30}]',
    }
    models.GeneralSetting.where(
        name='google_analytics_4_bigquery_dataset'
    ).first().update(value='test-ga4-dataset')

    # Required due to uncertainty around how to do actual integration
    # test with BigQuery locally.
    variables: list[ml_model.bigquery.Variable] = []
    client_mock.return_value.get_analytics_variables.return_value = variables

    response = self.client.get('/api/ml-models/variables', query_string=request)
    self.assertEqual(response.status_code, 400)

  def post_test_model(self):
    request = {
        'name': 'Test Model',
        'input': {
            'source': 'GOOGLE_ANALYTICS',
            'parameters': {
              'first_party_dataset': '',
              'first_party_table': ''
            }
        },
        'bigquery_dataset': {
            'name': 'test-dataset',
            'location': 'US'
        },
        'type': 'BOOSTED_TREE_REGRESSOR',
        'unique_id': 'CLIENT_ID',
        'hyper_parameters': [
            {'name': 'L1_REG', 'value': '1'},
            {'name': 'L2_REG', 'value': '1'},
            {'name': 'BOOSTER_TYPE', 'value': 'GBTREE'},
            {'name': 'MAX_ITERATIONS', 'value': '50'},
            {'name': 'SUBSAMPLE', 'value': '0.8'},
            {'name': 'TREE_METHOD', 'value': 'HIST'},
            {'name': 'ENABLE_GLOBAL_EXPLAIN', 'value': 'true'},
            {'name': 'NUM_PARALLEL_TREE', 'value': '2'},
            {'name': 'DATA_SPLIT_METHOD', 'value': 'AUTO_SPLIT'},
            {'name': 'EARLY_STOP', 'value': 'false'}
        ],
        'variables': [
          {
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS',
            'role': 'FEATURE',
            'key': None,
            'value_type': None
          },
          {
            'name': 'purchase',
            'source': 'FIRST_PARTY',
            'role': 'LABEL',
            'key': None,
            'value_type': None
          }
        ],
        'conversion_rate_segments': 0,
        'class_imbalance': 7,
        'timespans': [
            {'name': 'training', 'value': 20, 'unit': 'day'},
            {'name': 'predictive', 'value': 1, 'unit': 'day'}
        ],
        'output': {
            'destination': 'GOOGLE_ANALYTICS_MP_EVENT',
            'parameters': {
                'customer_id': '0',
                'conversion_action_id': '0',
                'average_conversion_value': 0.0
            }
        }
    }

    response = self.client.post('/api/ml-models', json=request)
    return (request, response)
