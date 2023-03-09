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
from typing import Union
import re

from controller.ml_model.templates import compiler

class TestCompiler(absltest.TestCase):

  @freeze_time("2023-02-06T00:00:00")
  def test_build_training_pipeline(self):
    test_model = self.model_config(
      type='LOGISTIC_REG',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'int',
        'is_score': True,
        'is_percentage': False
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

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

  def test_build_model_sql_first_party_and_google_analytics(self):
    test_model = self.model_config(
      type='LOGISTIC_REG',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'int',
        'is_score': True,
        'is_percentage': False
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

    pipeline = compiler.build_training_pipeline(test_model, 'test-project-id-1234', 'test-ga4-dataset-loc')
    self.assertEqual(pipeline['name'], 'Test Model - Training')
    self.assertEqual(pipeline['jobs'][0]['name'], 'Test Model - Training Setup')
    params = pipeline['jobs'][0]['params']

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

  def test_build_model_sql_first_party(self):
    test_model = self.model_config(
      type='LOGISTIC_REG',
      uses_first_party_data=True,
      label={
        'name': 'enroll',
        'source': 'FIRST_PARTY',
        'key': 'value',
        'value_type': 'int',
        'is_score': True,
        'is_percentage': False
      },
      features=[
        {'name': 'call', 'source': 'FIRST_PARTY'},
        {'name': 'request_for_info', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=0)

    pipeline = compiler.build_training_pipeline(test_model, 'test-project-id-1234', 'test-ga4-dataset-loc')
    params = pipeline['jobs'][0]['params']

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

    # skew-factor check
    self.assertNotIn(
      'MOD(ABS(FARM_FINGERPRINT(user_pseudo_id))',
      sql,
      'Skew-factor check failed. Should not exist when skew factor is set to 0.')

  def test_build_model_sql_google_analytics(self):
    test_model = self.model_config(
      type='LOGISTIC_REG',
      uses_first_party_data=False,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'int',
        'is_score': True,
        'is_percentage': False
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'GOOGLE_ANALYTICS'}
      ],
      skew_factor=4)

    pipeline = compiler.build_training_pipeline(test_model, 'test-project-id-1234', 'test-ga4-dataset-loc')
    params = pipeline['jobs'][0]['params']

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
      'Google Analytics label pull check failed.')

    self.assertRegex(
      sql,
      re.escape('SELECT * FROM analytics_variables'),
      'Google Analytics label join check failed.')

    # feature check
    self.assertRegex(
      sql,
      r',[\s\n]+'.join([
        re.escape('SUM(IF(name = "click", 1, 0)) AS cnt_click'),
        re.escape('SUM(IF(name = "subscribe", 1, 0)) AS cnt_subscribe'),
      ]),
      'Google Analytics feature check failed.')

  @freeze_time("2023-02-06T00:00:00")
  def test_build_predictive_pipeline(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'string,int',
        'is_score': True,
        'is_percentage': False,
        'is_conversion': False
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

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

    output_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)

    # check job start conditions
    self.assertEqual(output_job['hash_start_conditions'][0]['preceding_job_id'], setup_job['id'])

    params = output_job['params']

    # big-query dataset location check
    dataset_loc_param = next(param for param in params if param['name'] == 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # sql check start
    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)

    ga4_upload_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive GA4 Upload')
    self.assertIsNotNone(ga4_upload_job)

    # check job start conditions
    self.assertEqual(ga4_upload_job['hash_start_conditions'][0]['preceding_job_id'], output_job['id'])

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

  def test_build_predictive_sql_first_party_and_google_analytics(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'string,int',
        'is_score': True,
        'is_percentage': False,
        'is_conversion': True,
        'average_value': 1234
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    setup_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

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
        'WHERE name = "purchase"',
        'AND params.key = "value"',
        re.escape('AND COALESCE(params.value.string_value, params.value.int_value) NOT IN ("", "0", 0, NULL)')
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

    # timespan check
    self.assertIn(
      'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH))',
      sql,
      'Timespan start check failed.')

    self.assertIn(
      'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))',
      sql,
      'Timespan end check failed.')

  def test_build_predictive_sql_first_party(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_CLASSIFIER',
      uses_first_party_data=True,
      label={
        'name': 'premium_subscription',
        'source': 'FIRST_PARTY',
        'key': 'value',
        'value_type': 'int',
        'is_score': True,
        'is_percentage': False,
        'is_conversion': True,
        'average_value': 1234
      },
      features=[
        {'name': 'purchase', 'source': 'FIRST_PARTY'},
        {'name': 'request_for_info', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    setup_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # Probability check
    self.assertIn(
      '(SELECT prob FROM UNNEST(predicted_label_probs)) AS probability,',
      sql,
      'Probability not found in select when selecting from ML.PREDICT.'
    )

    # conversion label check
    self.assertRegex(
      sql,
      r',[\s\S]+'.join([
        'premium_subscription',
        re.escape('ML.PREDICT'),
      ]),
      'Conversion label check failed.')

    # user id check
    self.assertRegex(
      sql,
      r'[\s\S]+'.join([
        'SELECT',
        'user_id,',
        re.escape('ML.PREDICT')
      ]),
      'User id check failed.')

    # label check
    self.assertIn(
      'fp.premium_subscription AS label,',
      sql,
      'First party label check failed.')

    # feature check
    self.assertRegex(
      sql,
      r',[\s\n]+'.join([
        re.escape('fp.purchase'),
        re.escape('fp.request_for_info'),
      ]),
      'First party feature check failed.')

  def test_build_predictive_sql_google_analytics(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_CLASSIFIER',
      uses_first_party_data=False,
      label={
        'name': 'subscription',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'string',
        'is_score': True,
        'is_percentage': False,
        'is_conversion': False
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'scroll', 'source': 'GOOGLE_ANALYTICS'}
      ],
      skew_factor=4)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    setup_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # label check
    self.assertRegex(
      sql,
      r'[\s\n]+'.join([
        'WHERE name = "subscription"',
        'AND params.key = "value"',
        re.escape('AND COALESCE(params.value.string_value, params.value.int_value) NOT IN ("", "0", 0, NULL)')
      ]),
      'Google Analytics label pull check failed.')

    self.assertRegex(
      sql,
      re.escape('SELECT * FROM analytics_variables'),
      'Google Analytics label join check failed.')

    # feature check
    self.assertRegex(
      sql,
      r',[\s\n]+'.join([
        re.escape('SUM(IF(name = "click", 1, 0)) AS cnt_click'),
        re.escape('SUM(IF(name = "scroll", 1, 0)) AS cnt_scroll')
      ]),
      'Google Analytics feature check failed.')

  def test_build_output_sql_score(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'string,int',
        'is_score': True,
        'is_percentage': True,
        'is_conversion': True,
        'average_value': 1234
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # name check
    self.assertIn(
      'CREATE OR REPLACE TABLE `test-project-id-1234.test-dataset.output`',
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

    # conversion label check
    self.assertRegex(
      sql,
      re.escape('(SUM(purchase) / COUNT(normalized_score)) * 1234 AS value'),
      'Failed conversion label check within conversion rate calculation step.')

    self.assertRegex(
      sql,
      r'[\s\S]+'.join([
        re.escape('p.purchase,'),
        re.escape('FROM `test-project-id-1234.test-dataset.predictions`')
      ]),
      'Failed conversion label check within prediction preparation step.')

    self.assertRegex(
      sql,
      r'[\s\S]+'.join([
        re.escape('cr.value,'),
        re.escape('LEFT OUTER JOIN conversion_rate cr')
      ]),
      'Failed conversion rate check within ouput consolidation step.')

    # user id check
    self.assertIn(
      'p.user_id,',
      sql,
      'Failed user id check within prediction preparation step.')

  def test_build_output_sql_score_as_percentage(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'int',
        'is_score': True,
        'is_percentage': True,
        'is_conversion': False
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # label type check
    self.assertRegex(
      sql,
      r'[\n\s]+'.join([
        re.escape('p.predicted_label * 100 AS value,'),
        re.escape('p.predicted_label * 100 AS score,')
      ]),
      'Failed label type check within prediction preparation step. Expected percentage multiplier (100).')

  def test_build_output_sql_score_as_decimal(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'int',
        'is_score': True,
        'is_percentage': False,
        'is_conversion': False
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # label type check
    self.assertRegex(
      sql,
      r'[\n\s]+'.join([
        re.escape('p.predicted_label * 1 AS value,'),
        re.escape('p.predicted_label * 1 AS score,')
      ]),
      'Failed label type check within prediction preparation step. Expected no multiplier (1).')

  def test_build_output_sql_revenue(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'float',
        'is_score': False,
        'is_revenue': True,
        'is_conversion': False
      },
      features=[
        {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
        {'name': 'subscribe', 'source': 'FIRST_PARTY'}
      ],
      skew_factor=4)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = next(param for param in params if param['name'] == 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # name check
    self.assertIn(
      'CREATE OR REPLACE TABLE `test-project-id-1234.test-dataset.output`',
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

    # label output type check
    self.assertIn(
      'p.predicted_label AS revenue',
      sql,
      'Failed label output type check within prediction preparation step.')

    # user id check
    self.assertIn(
      'p.user_id,',
      sql,
      'Failed user id check within prediction preparation step.')

  def test_build_ga4_request(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=False,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'float',
        'is_score': False,
        'is_revenue': True,
        'is_conversion': False
      },
      features=[],
      skew_factor=0)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    upload_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive GA4 Upload')
    self.assertIsNotNone(upload_job)
    params = upload_job['params']

    # big-query dataset id check
    dataset_id_param = next(param for param in params if param['name'] == 'bq_dataset_id')
    self.assertIsNotNone(dataset_id_param)
    self.assertEqual(dataset_id_param['value'], 'test-dataset')

    # big-query dataset location check
    dataset_loc_param = next(param for param in params if param['name'] == 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # ga4 measurement id check
    measurement_id_param = next(param for param in params if param['name'] == 'measurement_id')
    self.assertIsNotNone(measurement_id_param)
    self.assertEqual(measurement_id_param['value'], 'test-ga4-measurement-id')

    # ga4 api secret check
    api_secret_param = next(param for param in params if param['name'] == 'api_secret')
    self.assertIsNotNone(api_secret_param)
    self.assertEqual(api_secret_param['value'], 'test-ga4-api-secret')

  def test_build_ga4_request_score(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'float',
        'is_score': True,
        'is_percentage': True,
        'is_conversion': False
      },
      features=[],
      skew_factor=0)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    upload_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive GA4 Upload')
    self.assertIsNotNone(upload_job)
    params = upload_job['params']

    # template check
    template_param = next(param for param in params if param['name'] == 'template')
    self.assertIsNotNone(template_param)

    self.assertJsonEqual(
      template_param['value'],
      r"""
        {
          "clientId": "${client_id}",
          "userId": "${user_id}",
          "nonPersonalizedAds": false,
          "events": [
            {
              "name": "${event_name}",
              "params": {
                "type": "${type}",
                "value": "${value}",
                "score": "${score}",
                "nscore": "${normalized_score}"
              }
            }
          ]
        }
      """,
      'Failed template check.')

  def test_build_ga4_request_revenue(self):
    test_model = self.model_config(
      type='BOOSTED_TREE_REGRESSOR',
      uses_first_party_data=True,
      label={
        'name': 'purchase',
        'source': 'GOOGLE_ANALYTICS',
        'key': 'value',
        'value_type': 'float',
        'is_score': False,
        'is_revenue': True,
        'is_conversion': False
      },
      features=[],
      skew_factor=0)

    pipeline = compiler.build_predictive_pipeline(
      test_model, 'test-project-id-1234', 'test-ga4-dataset-loc', 'test-ga4-measurement-id', 'test-ga4-api-secret')
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    upload_job = next(job for job in pipeline['jobs'] if job['name'] == 'Test Model - Predictive GA4 Upload')
    self.assertIsNotNone(upload_job)
    params = upload_job['params']

    # template check
    template_param = next(param for param in params if param['name'] == 'template')
    self.assertIsNotNone(template_param)

    self.assertJsonEqual(
      template_param['value'],
      r"""
        {
          "clientId": "${client_id}",
          "userId": "${user_id}",
          "nonPersonalizedAds": false,
          "events": [
            {
              "name": "${event_name}",
              "params": {
                "type": "${type}",
                "value": "${value}",
                "revenue": "${revenue}"
              }
            }
          ]
        }
      """,
      'Failed template check.')

  def model_config(self, type: str, uses_first_party_data: bool, label: dict,
                   features: list[dict], skew_factor: int):
    return self.convert_to_object({
      'name': 'Test Model',
      'bigquery_dataset': {
        'location': 'US',
        'name': 'test-dataset'
      },
      'type': type,
      'uses_first_party_data': uses_first_party_data,
      'hyper_parameters': [
        {'name': 'HP1-NAME', 'value': 'HP1-STRING'},
        {'name': 'HP2-NAME', 'value': '1'},
        {'name': 'HP3-NAME', 'value': '13.7'},
        {'name': 'HP4-NAME', 'value': 'true'},
        {'name': 'HP5-NAME', 'value': 'false'}
      ],
      'label': label,
      'features': features,
      'skew_factor': skew_factor,
      'timespans': [
        {"name": "training", "value": 17, "unit": "month"},
        {"name": "predictive", "value": 1, "unit": "month"}
      ]
    })

  def convert_to_object(self, collection: Union[dict,list]):
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
