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


"""Tests for controller.ml_model.templates.compiler."""

from absl.testing import absltest
from freezegun import freeze_time
import re

from controller.ml_model.templates import compiler

class TestCompiler(absltest.TestCase):

  @freeze_time("2023-02-06T00:00:00")
  def test_build_training_pipeline_first_party_and_google_analytics(self):
    test_model = self.convert_to_object({
      'name': 'Test Model',
      'bigquery_dataset': {
        'location': 'US',
        'name': 'test-dataset'
      },
      'type': 'LOGISTIC_REG',
      'uses_first_party_data': True,
      'hyper_parameters': [
        {'name': 'HP1-NAME', 'value': 'HP1-STRING'},
        {'name': 'HP2-NAME', 'value': '1'},
        {'name': 'HP3-NAME', 'value': '13.7'},
        {'name': 'HP4-NAME', 'value': 'true'},
        {'name': 'HP5-NAME', 'value': 'false'}
      ],
      'label': {
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'int'
      },
      'features': [
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      'skew_factor': 4,
      'timespans': [
        {"name": "training", "value": 17, "unit": "month"},
        {"name": "predictive", "value": 1, "unit": "month"}
      ]
    })

    pipeline = compiler.build_training_pipeline(test_model, 'test-project-id-1234', 'test-ga4-dataset-loc')
    self.assertEqual(pipeline['name'], 'Test Model - Training')
    self.assertEqual(pipeline['jobs'][0]['name'], 'Test Model - Training Setup')
    params = pipeline['jobs'][0]['params']

    # big-query dataset location check
    dataset_loc_param = next(param for param in params if param["name"] == "bq_dataset_location")
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # schedule check
    self.assertEqual(pipeline['schedules'][0]['cron'], '0 0 6 2,5,8,11 *')

    # sql check start
    sql_param = next(param for param in params if param["name"] == "script")
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # name check
    self.assertIn(
      'CREATE OR REPLACE MODEL `test-project-id-1234.test-dataset.model`',
      sql,
      'Model name check failed.')

    # event table name check
    self.assertIn(
      'FROM `test-project-id-1234.test-ga4-dataset-loc.events_*`',
      sql,
      'Event table name check failed.')

    # hyper-parameter check
    self.assertRegex(
      sql,
      r',[\s\n]+'.join([
        'HP1-NAME = "HP1-STRING"',
        'HP2-NAME = 1',
        'HP3-NAME = 13.7',
        'HP4-NAME = TRUE',
        'HP5-NAME = FALSE'
      ]),
      'Hyper-Parameter check failed.')

    # label check
    self.assertRegex(
      sql,
      r'[\s\n]+'.join([
        'WHERE name = "purchase"',
        'AND params.key = "value"',
        re.escape('AND COALESCE(params.value.int_value, params.value.float_value, params.value.double_value, 0) > 0')
      ]),
      'Google Analytics label pull check failed.')

    self.assertRegex(
      sql,
      re.escape('IFNULL(av.label, 0) AS label'),
      'Google Analytics label join check failed.')

    # feature check
    self.assertRegex(
      sql,
      re.escape('SUM(IF(name = "click", 1, 0)) AS cnt_click'),
      'Google Analytics feature check failed.')

    self.assertRegex(
      sql,
      re.escape('fp.subscribe'),
      'First party feature check failed.')

    # skew-factor check
    self.assertIn(
      'MOD(ABS(FARM_FINGERPRINT(user_pseudo_id)), 4)',
      sql,
      'Skew-factor check failed.')

    # timespan check
    self.assertIn(
      'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH))',
      sql,
      'Timespan start check failed.')

    self.assertIn(
      'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH))',
      sql,
      'Timespan end check failed.')

    # sql check end

  @freeze_time("2023-02-06T00:00:00")
  def test_build_training_pipeline_first_party(self):
    test_model = self.convert_to_object({
      'name': 'Test Model',
      'bigquery_dataset': {
        'location': 'US',
        'name': 'test-dataset'
      },
      'type': 'LOGISTIC_REG',
      'uses_first_party_data': True,
      'hyper_parameters': [
        {'name': 'HP1-NAME', 'value': 'HP1-STRING'},
        {'name': 'HP2-NAME', 'value': '1'},
        {'name': 'HP3-NAME', 'value': '13.7'},
        {'name': 'HP4-NAME', 'value': 'true'},
        {'name': 'HP5-NAME', 'value': 'false'}
      ],
      'label': {
        'name': 'enroll',
        'source': 'FIRST_PARTY',
        'key': 'value',
        'value_type': 'int'
      },
      'features': [
        {'name': 'call', 'source': 'FIRST_PARTY'},
        {'name': 'request_for_info', 'source': 'FIRST_PARTY'}
      ],
      'skew_factor': 4,
      'timespans': [
        {"name": "training", "value": 17, "unit": "month"},
        {"name": "predictive", "value": 1, "unit": "month"}
      ]
    })

    pipeline = compiler.build_training_pipeline(test_model, 'test-project-id-1234', 'test-ga4-dataset-loc')
    params = pipeline['jobs'][0]['params']

    # sql check start
    sql_param = next(param for param in params if param["name"] == "script")
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # label check
    self.assertRegex(
      sql,
      re.escape('fp.enroll'),
      'First party label check failed.')

    # feature check
    self.assertRegex(
      sql,
      r',[\s\n]+'.join([
        re.escape('fp.call'),
        re.escape('fp.request_for_info'),
      ]),
      'First party feature check failed.')

    # sql check end

  @freeze_time("2023-02-06T00:00:00")
  def test_build_training_pipeline_google_analytics(self):
    test_model = self.convert_to_object({
      'name': 'Test Model',
      'bigquery_dataset': {
        'location': 'US',
        'name': 'test-dataset'
      },
      'type': 'LOGISTIC_REG',
      'uses_first_party_data': False,
      'hyper_parameters': [
        {'name': 'HP1-NAME', 'value': 'HP1-STRING'},
        {'name': 'HP2-NAME', 'value': '1'},
        {'name': 'HP3-NAME', 'value': '13.7'},
        {'name': 'HP4-NAME', 'value': 'true'},
        {'name': 'HP5-NAME', 'value': 'false'}
      ],
      'label': {
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'int'
      },
      'features': [
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'GOOGLE_ANALYTICS'}
      ],
      'skew_factor': 4,
      'timespans': [
        {"name": "training", "value": 17, "unit": "month"},
        {"name": "predictive", "value": 1, "unit": "month"}
      ]
    })

    pipeline = compiler.build_training_pipeline(test_model, 'test-project-id-1234', 'test-ga4-dataset-loc')
    params = pipeline['jobs'][0]['params']

    # sql check start
    sql_param = next(param for param in params if param["name"] == "script")
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # label check
    self.assertRegex(
      sql,
      r'[\s\n]+'.join([
        'WHERE name = "purchase"',
        'AND params.key = "value"',
        re.escape('AND COALESCE(params.value.int_value, params.value.float_value, params.value.double_value, 0) > 0')
      ]),
      'Google Analytics label check failed.')

    # feature check
    self.assertRegex(
      sql,
      r',[\s\n]+'.join([
        re.escape('SUM(IF(name = "click", 1, 0)) AS cnt_click'),
        re.escape('SUM(IF(name = "subscribe", 1, 0)) AS cnt_subscribe'),
      ]),
      'Google Analytics feature check failed.')

    # sql check end

  @freeze_time("2023-02-06T00:00:00")
  def test_build_predictive_pipeline(self):
    test_model = self.convert_to_object({
      'name': 'Test Model',
      'bigquery_dataset': {
        'location': 'US',
        'name': 'test-dataset'
      },
      'type': 'LOGISTIC_REG',
      'hyper_parameters': [
        {'name': 'HP1-NAME', 'value': 'HP1-STRING'},
        {'name': 'HP2-NAME', 'value': '1'},
        {'name': 'HP3-NAME', 'value': '13.7'},
        {'name': 'HP4-NAME', 'value': 'true'},
        {'name': 'HP5-NAME', 'value': 'false'}
      ],
      'label': {
        'name': 'subscription',
        'source': 'FIRST_PARTY',
        'key': 'value',
        'value_type': 'string,int'
      },
      'features': [
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      'skew_factor': 4,
      'timespans': [
        {"name": "training", "value": 24, "unit": "month"},
        {"name": "predictive", "value": 4, "unit": "month"}
      ]
    })

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    setup_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    # big-query dataset location check
    dataset_loc_param = next(param for param in params if param['name'] == 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # schedule check
    self.assertEqual(pipeline['schedules'][0]['cron'], '0 0 * * *')

    # sql check start
    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # name check
    self.assertIn(
      'CREATE OR REPLACE TABLE `test-project-id-1234.test-dataset.predictions`',
      sql,
      'Predictions table name check failed.')

    # training table check
    self.assertIn(
      'FROM ML.PREDICT(MODEL `test-project-id-1234.test-dataset.model`',
      sql,
      'Not able to find training model dataset callout.')

    # event table name check
    self.assertIn(
      'FROM `test-project-id-1234.test-ga4-dataset-loc.events_*`',
      sql,
      'Event table name check failed.')

    # label check
    self.assertRegex(
      sql,
      r'[\s\n]+'.join([
        'WHERE name = "subscription"',
        'AND params.key = "package"',
        re.escape('AND COALESCE(params.value.string_value, params.value.int_value, 0) NOT IN ("", "0", 0, NULL)')
      ]),
      'Label check failed.')

    # feature check
    self.assertRegex(
      sql,
      r',[\s\n]+'.join([
        re.escape('SUM(IF(name = "click", 1, 0)) AS cnt_click'),
        re.escape('SUM(IF(name = "subscribe", 1, 0)) AS cnt_subscribe')
      ]),
      'Feature check failed.')

    # timespan check
    self.assertIn(
      'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 + 21 MONTH))',
      sql,
      'Timespan check failed.')

    # sql check end

    scores_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Scores')
    self.assertIsNotNone(scores_job)

    # check job start conditions
    self.assertEqual(scores_job['hash_start_conditions'][0]['preceding_job_id'], setup_job['id'])

    params = scores_job['params']

    # big-query dataset location check
    dataset_loc_param = next(param for param in params if param['name'] == 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # sql check start
    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # name check
    self.assertIn(
      'CREATE OR REPLACE TABLE `test-project-id-1234.test-dataset.scores`',
      sql,
      'Scores table name check failed.')

    # predictions table name check
    self.assertIn(
      'FROM `test-project-id-1234.test-dataset.predictions`',
      sql,
      'Predictions table name check failed.')

    # events table name check
    self.assertIn(
      'FROM `test-project-id-1234.test-ga4-dataset-loc.events_*`',
      sql,
      'Events table name check failed.')

    # summary table check
    self.assertIn(
      'FROM `test-project-id-1234.test-ga4-dataset-loc.__TABLES_SUMMARY__`',
      sql,
      'Summary table name check failed.')

    ga4_upload_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive GA4 Upload')
    self.assertIsNotNone(ga4_upload_job)

    # check job start conditions
    self.assertEqual(ga4_upload_job['hash_start_conditions'][0]['preceding_job_id'], scores_job['id'])

    params = ga4_upload_job['params']

    # project id check
    bq_project_id_param = next(param for param in params if param['name'] == 'bq_project_id')
    self.assertIsNotNone(bq_project_id_param)
    self.assertEqual(bq_project_id_param['value'], 'test-project-id-1234')

    # big-query dataset name check
    dataset_name_param = next(param for param in params if param['name'] == 'bq_dataset_id')
    self.assertIsNotNone(dataset_name_param)
    self.assertEqual(dataset_name_param['value'], 'test-dataset')

    # big-query dataset location check
    dataset_loc_param = next(param for param in params if param['name'] == 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # measurement id check
    measurement_id_param = next(param for param in params if param['name'] == 'measurement_id')
    self.assertIsNotNone(measurement_id_param)
    self.assertEqual(measurement_id_param['value'], 'test-ga4-measurement-id')

    # api secret check
    api_secret_param = next(param for param in params if param['name'] == 'api_secret')
    self.assertIsNotNone(api_secret_param)
    self.assertEqual(api_secret_param['value'], 'test-ga4-api-secret')

    # template check
    template_param = next(param for param in params if param['name'] == 'template')
    self.assertIsNotNone(template_param)

  def convert_to_object(self, collection: dict|list):
    class TempObject:
      pass

    if type(collection) == list:
      for key, value in enumerate(collection):
        collection[key] = self.convert_to_object(value)
    elif type(collection) == dict:
      temp = TempObject()
      for key, value in collection.items():
        temp.__dict__[key] = self.convert_to_object(value)
      return temp

    return collection


if __name__ == '__main__':
  absltest.main()
