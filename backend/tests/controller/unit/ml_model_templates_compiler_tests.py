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

import re
from typing import Union, Iterable, Any
from absl.testing import absltest
from absl.testing import parameterized
import freezegun

from controller import ml_model
from controller import models

class TestCompiler(parameterized.TestCase):

  @freezegun.freeze_time('2023-04-06T00:00:00')
  def test_build_training_pipeline(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Training')

    # schedule check
    self.assertEqual(pipeline['schedules'][0]['cron'], '0 0 6 4,7,10,1 *')

    # setup job check
    self.assertEqual(pipeline['jobs'][0]['name'], 'Test Model - Training Setup')
    params = pipeline['jobs'][0]['params']

    # big-query dataset location check
    dataset_loc_param = self.first(params, 'name', 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # sql check start
    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)

    # conversion value calculations job check
    self.assertEqual(
        pipeline['jobs'][1]['name'],
        'Test Model - Conversion Value Calculations')
    params = pipeline['jobs'][1]['params']

    # big-query dataset location check
    dataset_loc_param = self.first(params, 'name', 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # worker check
    self.assertEqual(pipeline['jobs'][0]['worker_class'], 'BQScriptExecutor')

    # sql check
    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    self.assertEqual(sql_param['type'], 'sql')
    self.assertNotEmpty(sql_param['value'])

  def test_build_model_sql_first_party_and_google_analytics(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'first_purchase_date',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'scroll',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'element_id',
            'comparison': 'EQUAL',
            'value': 'rfi_submit',
            'value_type': 'string'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Training')
    self.assertEqual(pipeline['jobs'][0]['name'], 'Test Model - Training Setup')
    params = pipeline['jobs'][0]['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # name check
    self.assertIn(
        'CREATE OR REPLACE MODEL '
        '`test-project-id-1234.test-dataset.predictive_model`',
        sql,
        'Model name check failed.')

    # event table name check
    self.assertIn(
        'FROM `GA4_PROJECT.GA4_DATASET.events_*`',
        sql,
        'Event table name check failed.')

    # first party table name check
    self.assertIn(
        'FROM `FP_PROJECT.FP_DATASET.FP_DATA_TABLE`',
        sql,
        'First party table name check failed.')

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
            re.escape(
                'AND COALESCE(params.value.int_value,'
                ' params.value.float_value, params.value.double_value,'
                ' 0) > 0'
            ),
        ]),
        'Google Analytics label pull check failed.')

    self.assertRegex(
        sql,
        re.escape('INNER JOIN analytics_variables'),
        'Google Analytics variables join check failed.')

    # standard feature check
    self.assertRegex(
        sql,
        re.escape('SUM(IF(e.name = "scroll", 1, 0)) AS cnt_scroll'),
        'Google Analytics feature check failed.')

    # advanced (comparison) feature check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('SUM(('),
          re.escape('SELECT 1'),
          re.escape('FROM UNNEST(e.params)'),
          re.escape('WHERE e.name = "click"'),
          re.escape('AND key = "element_id"'),
          re.escape('AND COALESCE(value.string_value, CAST(value.int_value AS STRING)) = "rfi_submit"'),
          re.escape(')) AS cnt_click_element_id_equal_rfi_submit')
        ]),
        'Google Analytics advanced feature check failed.')

    # standard feature check
    self.assertRegex(
        sql,
        re.escape('SUM(IF(e.name = "scroll", 1, 0)) AS cnt_scroll'),
        'Google Analytics feature check failed.')

    # first party variable check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('first_party_variables AS ('),
          re.escape('subscribe,'),
          re.escape('first_purchase_date AS trigger_date,')
        ]),
        'First party variable check failed.')

    # class-imbalance check
    self.assertIn(
        'MOD(ABS(FARM_FINGERPRINT(unique_id)), 100) <= ((1 / 4) * 100)',
        sql,
        'Class-Imbalance check failed.')

    # timespan check
    self.assertIn(
        'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))',
        sql,
        'Timespan start check failed.')

    self.assertIn(
        'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 13 DAY))',
        sql,
        'Timespan end check failed.')

  def test_build_model_sql_first_party(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='CLIENT_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'enroll',
            'source': 'FIRST_PARTY',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'CLIENT_ID',
            'name': 'google_clientid',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FIRST_VALUE',
            'name': 'first_purchase',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'first_purchase_date',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'call',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'request_for_info',
            'source': 'FIRST_PARTY'
          }
        ],
        source='FIRST_PARTY',
        class_imbalance=1)

    pipeline = self.compiler(test_model).build_training_pipeline()
    params = pipeline['jobs'][0]['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # first party table name check
    self.assertIn(
        'FROM `FP_PROJECT.FP_DATASET.FP_DATA_TABLE`',
        sql,
        'First party table name check failed.')

    # client id check
    self.assertRegex(
      sql,
      r'[\s\S]+'.join([
          re.escape('first_party_variables AS ('),
          re.escape('google_clientid AS unique_id')
      ]),
      'Unique id select check failed.')

    # label check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('enroll AS label,')
        ]),
        'First party label check failed.')

    # feature check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('call,'),
            re.escape('request_for_info,')
        ]),
        'First party feature check failed.',
    )

    # other variable check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('first_purchase AS first_value'),
            re.escape('first_purchase_date AS trigger_date')
        ]),
        'First party variable check failed.',
    )

    # timespan check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('FROM first_party_variables'),
            re.escape('DATETIME(DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) AND'),
            re.escape('DATETIME_SUB(DATETIME(DATE_SUB(CURRENT_DATE(), INTERVAL 12 DAY)), INTERVAL 1 SECOND)')
        ]),
        'First party timespan check failed.',
    )

    # class-imbalance check
    self.assertNotIn(
        'MOD(ABS(FARM_FINGERPRINT(user_pseudo_id)), 100) > ((1 / 4) * 100)',
        sql,
        'Class-Imbalance check failed. Should not exist when class imbalance is'
        ' set to 1.'
    )

  def test_build_model_sql_google_analytics(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'page_view',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'page_location',
            'comparison': 'REGEX',
            'value': 'signup\/welcome\?[0-9]+',
            'value_type': 'string'
          },
          {
            'role': 'FEATURE',
            'name': 'game_score',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'comparison': 'GREATER',
            'value': '100',
            'value_type': 'int'
          },
          {
            'role': 'FEATURE',
            'name': 'game_purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'comparison': 'GREATER_OR_EQUAL',
            'value': '10.50',
            'value_type': 'float'
          },
          {
            'role': 'FEATURE',
            'name': 'game_open',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'comparison': 'LESS',
            'value': '10',
            'value_type': 'int'
          },
          {
            'role': 'FEATURE',
            'name': 'game_losses',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'amount',
            'comparison': 'LESS_OR_EQUAL',
            'value': '4',
            'value_type': 'int'
          },
          {
            'role': 'FEATURE',
            'name': 'game_category',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'comparison': 'EQUAL',
            'value': 'RPG',
            'value_type': 'string'
          },
          {
            'role': 'FEATURE',
            'name': 'game_title',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'comparison': 'NOT_EQUAL',
            'value': 'Through It All',
            'value_type': 'string'
          }
        ],
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()
    params = pipeline['jobs'][0]['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # label check
    self.assertRegex(
        sql,
        r'[\s\n]+'.join([
            'WHERE name = "purchase"',
            'AND params.key = "value"',
            re.escape(
                'AND COALESCE(params.value.int_value,'
                ' params.value.float_value, params.value.double_value,'
                ' 0) > 0'
            ),
        ]),
        'Google Analytics label pull check failed.')

    self.assertRegex(
        sql,
        re.escape('FROM analytics_variables'),
        'Google Analytics variables pull check failed.')

    # standard feature check
    self.assertRegex(
        sql,
        r',[\s\n]+'.join([
            re.escape('SUM(IF(e.name = "click", 1, 0)) AS cnt_click'),
            re.escape('SUM(IF(e.name = "subscribe", 1, 0)) AS cnt_subscribe'),
        ]),
        'Google Analytics standard feature check failed.')

    # advanced (comparison) feature check - regex
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('SUM(('),
          re.escape('SELECT 1'),
          re.escape('FROM UNNEST(e.params)'),
          re.escape('WHERE e.name = "page_view"'),
          re.escape('AND key = "page_location"'),
          re.escape('AND REGEXP_CONTAINS(value.string_value, r"signup\/welcome\?[0-9]+")'),
          re.escape(')) AS cnt_page_view_page_location_regex_signupwelcome09')
        ]),
        'Google Analytics advanced feature (REGEX) check failed.')

    # advanced (comparison) feature check - greater
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('AND CAST(COALESCE(value.string_value, value.int_value, value.float_value, value.double_value) AS NUMERIC) > 100'),
          re.escape(')) AS cnt_game_score_value_greater_100')
        ]),
        'Google Analytics advanced feature (GREATER) check failed.')

    # advanced (comparison) feature check - greater or equal
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('AND CAST(COALESCE(value.string_value, value.int_value, value.float_value, value.double_value) AS NUMERIC) >= 10.50'),
          re.escape(')) AS cnt_game_purchase_value_greater_or_equal_1050')
        ]),
        'Google Analytics advanced feature (GREATER_OR_EQUAL) check failed.')

    # advanced (comparison) feature check - less
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('AND CAST(COALESCE(value.string_value, value.int_value, value.float_value, value.double_value) AS NUMERIC) < 10'),
          re.escape(')) AS cnt_game_open_value_less_10')
        ]),
        'Google Analytics advanced feature (LESS) check failed.')

    # advanced (comparison) feature check - less or equal
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('AND CAST(COALESCE(value.string_value, value.int_value, value.float_value, value.double_value) AS NUMERIC) <= 4'),
          re.escape(')) AS cnt_game_losses_amount_less_or_equal_4')
        ]),
        'Google Analytics advanced feature (LESS_OR_EQUAL) check failed.')

    # advanced (comparison) feature check - equal
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('AND COALESCE(value.string_value, CAST(value.int_value AS STRING)) = "RPG"'),
          re.escape(')) AS cnt_game_category_value_equal_rpg')
        ]),
        'Google Analytics advanced feature (EQUAL) check failed.')

    # advanced (comparison) feature check - not equal
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('AND COALESCE(value.string_value, CAST(value.int_value AS STRING)) = "RPG"'),
          re.escape(')) AS cnt_game_title_value_not_equal_throughitall')
        ]),
        'Google Analytics advanced feature (NOT_EQUAL) check failed.')

  def test_build_model_sql_google_analytics_regression_model(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_REGRESSOR',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'FIRST_VALUE',
            'name': 'first_purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'GOOGLE_ANALYTICS'
          }
        ],
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()
    params = pipeline['jobs'][0]['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # first value join check
    self.assertRegex(
        sql,
        r'[\s\S]*'.join([
            re.escape('analytics_variables AS ('),
            re.escape('LEFT OUTER JOIN ('),
            re.escape('WHERE name = "first_purchase"'),
            re.escape('AND params.key = "value"'),
            re.escape(') t')
        ]),
        'Google Analytics first value join check failed.')

    # proper label and total value assignment check
    self.assertIn(
        '(label - first_value) AS label',
        sql,
        'Output label check failed.')

  def test_build_model_sql_google_analytics_regression_model_label_as_first_value(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_REGRESSOR',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'GOOGLE_ANALYTICS'
          }
        ],
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()
    params = pipeline['jobs'][0]['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # first value join check
    self.assertRegex(
        sql,
        r'[\s\S]*'.join([
            re.escape('analytics_variables AS ('),
            re.escape('LEFT OUTER JOIN ('),
            re.escape('WHERE name = "purchase"'),
            re.escape('AND params.key = "value"'),
            re.escape(') t')
        ]),
        'Google Analytics first value join check failed.')

    # proper label and total value assignment check
    self.assertIn(
        '(label - first_value) AS label',
        sql,
        'Output label check failed.')

  def test_build_model_sql_google_analytics_classification_model(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'GOOGLE_ANALYTICS'
          }
        ],
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()
    params = pipeline['jobs'][0]['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # random 90% selection check
    self.assertIn(
        'AND MOD(ABS(FARM_FINGERPRINT(user_pseudo_id)), 100) < 90',
        sql,
        'Google Analytics random 90% selection check failed.')

  def test_build_conversion_values_sql_first_party_and_google_analytics(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string,int'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'first_purchase_date',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()

    setup_job = self.first(pipeline['jobs'], 'name', 'Test Model - Conversion Value Calculations')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # name check
    self.assertIn(
        'CREATE OR REPLACE TABLE `test-project-id-1234.test-dataset.conversion_values`',
        sql,
        'Predictions table name check failed.')

    # training table check
    self.assertIn(
        'FROM ML.PREDICT(MODEL `test-project-id-1234.test-dataset.predictive_model`',
        sql,
        'Not able to find training model dataset callout.')

    # event table name check
    self.assertIn(
        'FROM `GA4_PROJECT.GA4_DATASET.events_*`',
        sql,
        'Event table name check failed.')

    # first party table name check
    self.assertIn(
        'FROM `FP_PROJECT.FP_DATASET.FP_DATA_TABLE`',
        sql,
        'First party table name check failed.')

    # label check
    self.assertRegex(
        sql,
        r'[\s\n]+'.join([
            'WHERE name = "purchase"',
            'AND params.key = "value"',
            re.escape('AND COALESCE(params.value.string_value, CAST(params.value.int_value AS STRING)) NOT IN ("", "0", NULL)')
        ]),
        'Google Analytics label pull check failed.')

    self.assertRegex(
        sql,
        re.escape('INNER JOIN analytics_variables'),
        'Google Analytics variables join check failed.')

    # feature check
    self.assertRegex(
        sql,
        re.escape('SUM(IF(e.name = "click", 1, 0)) AS cnt_click'),
        'Google Analytics feature check failed.')

    # first party variable check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
          re.escape('first_party_variables AS ('),
          re.escape('subscribe,'),
          re.escape('first_purchase_date AS trigger_date,')
        ]),
        'First party variable check failed.')

    # timespan check
    self.assertIn(
        'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))',
        sql,
        'Timespan start check failed.')

    self.assertIn(
        'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 13 DAY))',
        sql,
        'Timespan end check failed.')

    # ntile (conversion rate segments) check
    self.assertIn(
        'NTILE(10) OVER (ORDER BY plp.prob ASC)',
        sql,
        'Conversion rate segments check failed.')

    # average value check
    self.assertIn(
        '(SUM(label) / COUNT(1)) * 1234.5 AS value,',
        sql,
        'Average value check failed.')

    # probability check
    self.assertIn(
        'plp.prob AS probability,',
        sql,
        'Probability not found in select when selecting from ML.PREDICT.')

  def test_build_conversion_values_sql_first_party(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'premium_subscription',
            'source': 'FIRST_PARTY',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'FIRST_VALUE',
            'name': 'first_purchase',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'first_purchase_date',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'purchase',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'request_for_info',
            'source': 'FIRST_PARTY'
          }
        ],
        source='FIRST_PARTY',
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()

    setup_job = self.first(pipeline['jobs'], 'name', 'Test Model - Conversion Value Calculations')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # first party table name check
    self.assertIn(
        'FROM `FP_PROJECT.FP_DATASET.FP_DATA_TABLE`',
        sql,
        'First party table name check failed.')

    # label check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('premium_subscription AS label,')
        ]),
        'First party label check failed.')

    # feature check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('purchase,'),
            re.escape('request_for_info,'),
        ]),
        'First party feature check failed.')

    # other variable check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('first_purchase AS first_value,')
        ]),
        'First party variable check failed.',
    )

  def test_build_conversion_values_sql_google_analytics(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'subscription',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'scroll',
            'source': 'GOOGLE_ANALYTICS'
          }
        ],
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_training_pipeline()

    setup_job = self.first(pipeline['jobs'], 'name', 'Test Model - Conversion Value Calculations')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # label check
    self.assertRegex(
        sql,
        r'[\s\n]+'.join([
            'WHERE name = "subscription"',
            'AND params.key = "value"',
            re.escape('AND COALESCE(params.value.string_value, CAST(params.value.int_value AS STRING)) NOT IN ("", "0", NULL)')
        ]),
        'Google Analytics label pull check failed.')

    self.assertRegex(
        sql,
        re.escape('FROM analytics_variables'),
        'Google Analytics variables pull check failed.')

    # feature check
    self.assertRegex(
        sql,
        r',[\s\n]+'.join([
            re.escape('SUM(IF(e.name = "click", 1, 0)) AS cnt_click'),
            re.escape('SUM(IF(e.name = "scroll", 1, 0)) AS cnt_scroll')
        ]),
        'Google Analytics feature check failed.')

  @parameterized.named_parameters(
      ('destination google analytics custom event',
       'GOOGLE_ANALYTICS_MP_EVENT'),
      ('destination google ads conversion event',
       'GOOGLE_ADS_OFFLINE_CONVERSION')
  )
  def test_build_predictive_pipeline(self, destination: str):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string,int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        class_imbalance=4,
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        destination=destination)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    # schedule check
    self.assertEqual(pipeline['schedules'][0]['cron'], '0 0 * * *')

    setup_job = self.first(pipeline['jobs'], 'name', 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)

    # check job worker
    self.assertEqual(setup_job['worker_class'], 'BQScriptExecutor')

    params = setup_job['params']

    # big-query dataset location check
    dataset_loc_param = self.first(params, 'name', 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # sql script check
    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)

    output_job = self.first(pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)

    # check job start conditions
    self.assertEqual(
        output_job['hash_start_conditions'][0]['preceding_job_id'],
        setup_job['id'])

    # check job worker
    self.assertEqual(output_job['worker_class'], 'BQScriptExecutor')

    params = output_job['params']

    # big-query dataset location check
    dataset_loc_param = self.first(params, 'name', 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # sql script check
    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)

    upload_job = self.first(pipeline['jobs'], 'name', 'Test Model - Predictive Upload')
    self.assertIsNotNone(upload_job)

    # check job start conditions
    self.assertEqual(
        upload_job['hash_start_conditions'][0]['preceding_job_id'], output_job['id'])

    params = upload_job['params']

    # check destination specific parts
    if destination == 'GOOGLE_ANALYTICS_MP_EVENT':
      # check job worker
      self.assertEqual(upload_job['worker_class'], 'BQToMeasurementProtocolGA4')

      # measurement id check
      measurement_id_param = self.first(params, 'name', 'measurement_id')
      self.assertIsNotNone(measurement_id_param)
      self.assertEqual(measurement_id_param['value'], 'test-ga4-measurement-id')

      # api secret check
      api_secret_param = self.first(params, 'name', 'api_secret')
      self.assertIsNotNone(api_secret_param)
      self.assertEqual(api_secret_param['value'], 'test-ga4-api-secret')
    elif destination == 'GOOGLE_ADS_OFFLINE_CONVERSION':
      # check job worker
      self.assertEqual(upload_job['worker_class'], 'BQToAdsOfflineClickConversion')

    # project id check
    bq_project_id_param = self.first(params, 'name', 'bq_project_id')
    self.assertIsNotNone(bq_project_id_param)
    self.assertEqual(bq_project_id_param['value'], 'test-project-id-1234')

    # big-query dataset name check
    dataset_name_param = self.first(params, 'name', 'bq_dataset_id')
    self.assertIsNotNone(dataset_name_param)
    self.assertEqual(dataset_name_param['value'], 'test-dataset')

    # big-query dataset location check
    dataset_loc_param = self.first(params, 'name', 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # template check
    template_param = self.first(params, 'name', 'template')
    self.assertIsNotNone(template_param)

  def test_build_predictive_sql_first_party_and_google_analytics(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string,int'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'first_purchase_date',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    setup_job = self.first(pipeline['jobs'], 'name', 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # name check
    self.assertIn(
        'CREATE OR REPLACE TABLE `test-project-id-1234.test-dataset.predictions`',
        sql,
        'Predictions table name check failed.')

    # training table check
    self.assertIn(
        'FROM ML.PREDICT(MODEL `test-project-id-1234.test-dataset.predictive_model`',
        sql,
        'Not able to find training model dataset callout.')

    # event table name check
    self.assertIn(
        'FROM `GA4_PROJECT.GA4_DATASET.events_*`',
        sql,
        'Event table name check failed.')

    # first party table name check
    self.assertIn(
        'FROM `FP_PROJECT.FP_DATASET.FP_DATA_TABLE`',
        sql,
        'First party table name check failed.')

    # label check
    self.assertRegex(
        sql,
        r'[\s\n]+'.join([
            'WHERE name = "purchase"',
            'AND params.key = "value"',
            re.escape('AND COALESCE(params.value.string_value, CAST(params.value.int_value AS STRING)) NOT IN ("", "0", NULL)')
        ]),
        'Google Analytics label pull check failed.')

    self.assertRegex(
        sql,
        re.escape('INNER JOIN analytics_variables'),
        'Google Analytics variables join check failed.')

    # feature check
    self.assertRegex(
        sql,
        re.escape('SUM(IF(e.name = "click", 1, 0)) AS cnt_click'),
        'Google Analytics feature check failed.')

    # first party variables
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('subscribe,'),
            re.escape('first_purchase_date AS trigger_date,')
        ]),
        'First party variable check failed.')

    # timespan check
    self.assertIn(
        'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))',
        sql,
        'Timespan start check failed.')

    self.assertIn(
        'FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))',
        sql,
        'Timespan end check failed.')

  def test_build_predictive_sql_first_party(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'premium_subscription',
            'source': 'FIRST_PARTY',
            'key': 'value',
            'value_type': 'int'
          },
          {
            'role': 'USER_ID',
            'name': 'user_ident',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FIRST_VALUE',
            'name': 'first_purchase',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'first_purchase_date',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'purchase',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'request_for_info',
            'source': 'FIRST_PARTY'
          }
        ],
        source='FIRST_PARTY',
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    setup_job = self.first(pipeline['jobs'], 'name', 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # first party table name check
    self.assertIn(
        'FROM `FP_PROJECT.FP_DATASET.FP_DATA_TABLE`',
        sql,
        'First party table name check failed.')

    # probability check
    self.assertIn(
        'plp.prob AS probability,',
        sql,
        'Probability not found in select when selecting from ML.PREDICT.')

    # user ids check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            'SELECT',
            'unique_id,',
            re.escape('ML.PREDICT')
        ]),
        'Top level unique id check failed.')

    self.assertRegex(
      sql,
      r'[\s\S]+'.join([
          re.escape('first_party_variables AS ('),
          re.escape('user_ident AS unique_id')
      ]),
      'Initial unique id select check failed.')

    # label check
    self.assertRegex(
      sql,
      r'[\s\S]+'.join([
          re.escape('first_party_variables AS ('),
          re.escape('premium_subscription AS label,')
      ]),
      'First party label check failed.')

    # feature check
    self.assertRegex(
      sql,
      r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('purchase,'),
            re.escape('request_for_info,'),
        ]),
        'First party feature check failed.')

    # other variable check
    self.assertRegex(
      sql,
      r'[\s\S]+'.join([
            re.escape('first_party_variables AS ('),
            re.escape('first_purchase AS first_value,')
        ]),
        'First party variable check failed.',
    )

    # timespan check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('FROM first_party_variables'),
            re.escape('DATETIME(DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)) AND'),
            re.escape('DATETIME_SUB(DATETIME(DATE_SUB(CURRENT_DATE(), INTERVAL 0 DAY)), INTERVAL 1 SECOND)')
        ]),
        'First party timespan check failed.',
    )

  def test_build_predictive_sql_google_analytics(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        variables=[
          {
            'role': 'LABEL',
            'name': 'subscription',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'scroll',
            'source': 'GOOGLE_ANALYTICS'
          }
        ],
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    setup_job = self.first(pipeline['jobs'], 'name', 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # label check
    self.assertRegex(
        sql,
        r'[\s\n]+'.join([
            'WHERE name = "subscription"',
            'AND params.key = "value"',
            re.escape('AND COALESCE(params.value.string_value, CAST(params.value.int_value AS STRING)) NOT IN ("", "0", NULL)')
        ]),
        'Google Analytics label pull check failed.')

    self.assertRegex(
        sql,
        re.escape('FROM analytics_variables'),
        'Google Analytics pull check failed.')

    # feature check
    self.assertRegex(
        sql,
        r',[\s\n]+'.join([
            re.escape('SUM(IF(e.name = "click", 1, 0)) AS cnt_click'),
            re.escape('SUM(IF(e.name = "scroll", 1, 0)) AS cnt_scroll')
        ]),
        'Google Analytics feature check failed.')

  def test_build_predictive_sql_google_analytics_regression_model(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_REGRESSOR',
        variables=[
          {
            'role': 'LABEL',
            'name': 'subscription',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'scroll',
            'source': 'GOOGLE_ANALYTICS'
          }
        ],
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    setup_job = self.first(pipeline['jobs'], 'name', 'Test Model - Predictive Setup')
    self.assertIsNotNone(setup_job)
    params = setup_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # first value join check
    self.assertRegex(
        sql,
        r'[\s\S]*'.join([
            re.escape('analytics_variables AS ('),
            re.escape('LEFT OUTER JOIN ('),
            re.escape(
                'COALESCE(params.value.int_value, params.value.float_value,'
                ' params.value.double_value, 0) AS value'
            ),
            re.escape(') t'),
        ]),
        'Google Analytics first value join check failed.')

    # proper label and total value assignment check
    self.assertRegex(
        sql,
        r'[\s\S]*'.join([
            re.escape('label AS total_value,'),
            re.escape('(label - first_value) AS label'),
        ]),
        'Output label and total_value check failed.')

  def test_build_output_sql_google_analytics_in_source(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string,int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        class_imbalance=4,
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        destination='GOOGLE_ADS_OFFLINE_CONVERSION')

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # latest table suffix check
    self.assertIn(
        'SET _LATEST_TABLE_SUFFIX = (',
        sql,
        'Check for latest table suffix variable failed.')

    # events block check
    self.assertIn(
        'FROM `GA4_PROJECT.GA4_DATASET.events_*`',
        sql,
        'Check for events block failed.')

  def test_build_output_sql_first_party_in_source(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'USER_ID',
            'name': 'customer_id',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'timestamp',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'GCLID',
            'name': 'google_clickid',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'phone_call',
            'source': 'FIRST_PARTY'
          }
        ],
        class_imbalance=4,
        source='FIRST_PARTY',
        destination='GOOGLE_ADS_OFFLINE_CONVERSION')

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # latest table suffix check
    self.assertNotIn(
        'SET _LATEST_TABLE_SUFFIX = (',
        sql,
        'Check to ensure latest table suffix variable not included failed.')

    # events block check
    self.assertNotIn(
        'FROM `GA4_PROJECT.GA4_DATASET.events_*`',
        sql,
        'Check to ensure events block not included failed.')

    # first party block check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('first_party AS ('),
            re.escape('customer_id AS unique_id'),
            re.escape('google_clickid AS gclid'),
            re.escape('FROM `FP_PROJECT.FP_DATASET.FP_DATA_TABLE`'),
            re.escape('WHERE timestamp BETWEEN')
        ]),
        'Check for first party block failed.')

  def test_build_output_sql_classification_model(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string,int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = self.first(params, 'name', 'script')
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
        'FROM `GA4_PROJECT.GA4_DATASET.events_*`',
        sql,
        'Events table name check failed.')

    # summary table check
    self.assertIn(
        'FROM `GA4_PROJECT.GA4_DATASET.__TABLES_SUMMARY__`',
        sql,
        'Summary table name check failed.')

    # conversion values join check
    self.assertIn(
        'LEFT OUTER JOIN'
        ' `test-project-id-1234.test-dataset.conversion_values` cv',
        sql,
        'Failed conversion values join check.')

    # user id check
    self.assertIn(
        'p.user_id,',
        sql,
        'Failed user id check within prediction preparation step.')

    # score check
    self.assertIn(
        'MAX(p.probability) * 100 AS score',
        sql,
        'Failed score check within prediction preparation step.')

  def test_build_output_sql_regression_model(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_REGRESSOR',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'float'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        class_imbalance=4)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = self.first(params, 'name', 'script')
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
        'FROM `GA4_PROJECT.GA4_DATASET.events_*`',
        sql,
        'Events table name check failed.')

    # summary table check
    self.assertIn(
        'FROM `GA4_PROJECT.GA4_DATASET.__TABLES_SUMMARY__`',
        sql,
        'Summary table name check failed.')

    # revenue check
    self.assertIn(
        'IF(predicted_label > 0, ROUND(predicted_label, 4), 0) AS revenue',
        sql,
        'Failed label revenue check within prediction preparation step.')

    # user id check
    self.assertIn(
        'user_id,',
        sql,
        'Failed user id check within prediction preparation step.')

  def test_build_output_sql_google_analytics_mp_event(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string,int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        class_imbalance=4,
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        destination='GOOGLE_ANALYTICS_MP_EVENT')

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # consolidated output block check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('p.* EXCEPT(unique_id, user_pseudo_id, user_id)'),
            re.escape('p.user_pseudo_id AS client_id'),
            re.escape('p.unique_id AS user_id'),
            re.escape('"Predicted_Value" AS type'),
            re.escape('INNER JOIN users_without_score')
        ]),
        'Check for correct consolidated output block failed.')

  def test_build_output_sql_google_analytics_mp_event_first_party_only(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='CLIENT_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'CLIENT_ID',
            'name': 'ga_customer_id',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'timestamp',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'phone_call',
            'source': 'FIRST_PARTY'
          }
        ],
        class_imbalance=4,
        source='FIRST_PARTY',
        destination='GOOGLE_ANALYTICS_MP_EVENT')

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # first party users without scores
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('users_without_score AS ('),
            re.escape('FROM first_party')
        ]),
        'Check for correct users without scores block failed.')

    # consolidated output block check
    self.assertRegex(
        sql,
        r'[\s\S]+'.join([
            re.escape('p.* EXCEPT(unique_id)'),
            re.escape('p.unique_id AS client_id'),
            re.escape('"Predicted_Value" AS type')
        ]),
        'Check for correct consolidated output block failed.')

  def test_build_output_sql_google_ads_offline_conversion(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'string,int'
          },
          {
            'role': 'FEATURE',
            'name': 'click',
            'source': 'GOOGLE_ANALYTICS'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        class_imbalance=4,
        source='GOOGLE_ANALYTICS_AND_FIRST_PARTY',
        destination='GOOGLE_ADS_OFFLINE_CONVERSION')

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # check gclid pulled from google analytics
    self.assertIn(
        'params.value.string_value AS gclid',
        sql,
        'Check gclid pulled from google analytics failed.')

    # consolidated output block check
    self.assertIn(
        'g.gclid',
        sql,
        'Check for correct consolidated output block failed.')

  def test_build_output_sql_google_ads_offline_conversion_first_party_only(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'USER_ID',
            'name': 'customer_id',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'GCLID',
            'name': 'google_click_id',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'TRIGGER_DATE',
            'name': 'timestamp',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'phone_call',
            'source': 'FIRST_PARTY'
          },
          {
            'role': 'FEATURE',
            'name': 'subscribe',
            'source': 'FIRST_PARTY'
          }
        ],
        class_imbalance=4,
        source='FIRST_PARTY',
        destination='GOOGLE_ADS_OFFLINE_CONVERSION')

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    output_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Output')
    self.assertIsNotNone(output_job)
    params = output_job['params']

    sql_param = self.first(params, 'name', 'script')
    self.assertIsNotNone(sql_param)
    sql = sql_param['value']

    # check gclid, unique_id, and datetime pulled from first party table
    self.assertRegex(
        sql,
        r'[\s\n]+'.join([
            re.escape('unique_id,'),
            re.escape('gclid,'),
            re.escape('FORMAT_TIMESTAMP("%F %T%Ez", TIMESTAMP(timestamp)) AS datetime'),
            re.escape('FROM first_party')
        ]),
        'Check to ensure gclid, unique_id, and datetime pull from first party table failed.')

    # consolidated output block check
    self.assertIn(
        'g.gclid',
        sql,
        'Check for correct consolidated output block failed.')

  def test_build_ga4_request(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_REGRESSOR',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'float'
          }
        ],
        class_imbalance=0)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    upload_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Upload')
    self.assertIsNotNone(upload_job)
    params = upload_job['params']

    # big-query dataset id check
    dataset_id_param = self.first(params, 'name', 'bq_dataset_id')
    self.assertIsNotNone(dataset_id_param)
    self.assertEqual(dataset_id_param['value'], 'test-dataset')

    # big-query dataset location check
    dataset_loc_param = self.first(params, 'name', 'bq_dataset_location')
    self.assertIsNotNone(dataset_loc_param)
    self.assertEqual(dataset_loc_param['value'], 'US')

    # ga4 measurement id check
    measurement_id_param = self.first(params, 'name', 'measurement_id')
    self.assertIsNotNone(measurement_id_param)
    self.assertEqual(measurement_id_param['value'], 'test-ga4-measurement-id')

    # ga4 api secret check
    api_secret_param = self.first(params, 'name', 'api_secret')
    self.assertIsNotNone(api_secret_param)
    self.assertEqual(api_secret_param['value'], 'test-ga4-api-secret')

  def test_build_google_analytics_mp_event_score(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_CLASSIFIER',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'float'
          }
        ],
        class_imbalance=0)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    upload_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Upload')
    self.assertIsNotNone(upload_job)
    params = upload_job['params']

    # template check
    template_param = self.first(params, 'name', 'template')
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

  def test_build_google_analytics_mp_event_revenue(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_REGRESSOR',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'float'
          }
        ],
        class_imbalance=0)

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    upload_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Upload')
    self.assertIsNotNone(upload_job)
    params = upload_job['params']

    # template check
    template_param = self.first(params, 'name', 'template')
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

  def test_build_google_ads_offline_conversion(self):
    test_model = self.model_config(
        model_type='BOOSTED_TREE_REGRESSOR',
        unique_id='USER_ID',
        variables=[
          {
            'role': 'LABEL',
            'name': 'purchase',
            'source': 'GOOGLE_ANALYTICS',
            'key': 'value',
            'value_type': 'float'
          }
        ],
        class_imbalance=0,
        destination='GOOGLE_ADS_OFFLINE_CONVERSION')

    pipeline = self.compiler(test_model).build_predictive_pipeline()
    self.assertEqual(pipeline['name'], 'Test Model - Predictive')

    upload_job = self.first(
        pipeline['jobs'], 'name', 'Test Model - Predictive Upload')
    self.assertIsNotNone(upload_job)
    params = upload_job['params']

    # template check
    template_param = self.first(params, 'name', 'template')
    self.assertIsNotNone(template_param)

    self.assertIn(
        'customers/1234/conversionActions/5678',
        template_param['value'],
        'Failed template check.')

  def model_config(self,
                   model_type: str,
                   variables: list[dict[str, Any]],
                   class_imbalance: int,
                   unique_id: str = 'CLIENT_ID',
                   source: str = 'GOOGLE_ANALYTICS',
                   destination: str = 'GOOGLE_ANALYTICS_MP_EVENT'):
    return self.convert_to_object({
        'name': 'Test Model',
        'input': {
          'source': source,
          'parameters': {
            'google_analytics_project': 'GA4_PROJECT',
            'google_analytics_dataset': 'GA4_DATASET',
            'first_party_project': 'FP_PROJECT',
            'first_party_dataset': 'FP_DATASET',
            'first_party_table': 'FP_DATA_TABLE'
          }
        },
        'bigquery_dataset': {
            'location': 'US',
            'name': 'test-dataset'
        },
        'type': model_type,
        'unique_id': unique_id,
        'hyper_parameters': [
            {'name': 'HP1-NAME', 'value': 'HP1-STRING'},
            {'name': 'HP2-NAME', 'value': '1'},
            {'name': 'HP3-NAME', 'value': '13.7'},
            {'name': 'HP4-NAME', 'value': 'true'},
            {'name': 'HP5-NAME', 'value': 'false'}
        ],
        'variables': variables,
        'conversion_rate_segments':
            10 if model_type.endswith('CLASSIFIER') else 0,
        'class_imbalance': class_imbalance,
        'timespans': [
            {'name': 'training', 'value': 17, 'unit': 'day'},
            {'name': 'predictive', 'value': 1, 'unit': 'day'},
            {'name': 'exclusion', 'value': 10, 'unit': 'day'}
        ],
        'output': {
            'destination': destination,
            'parameters': {
                'customer_id': 1234,
                'conversion_action_id': 5678,
                'average_conversion_value': 1234.5
            }
        }
    })

  def compiler(self, model: models.MlModel):
    return ml_model.compiler.Compiler(
        project_id='test-project-id-1234',
        ga4_measurement_id='test-ga4-measurement-id',
        ga4_api_secret='test-ga4-api-secret',
        ml_model=model)

  def convert_to_object(
      self,
      collection: Union[dict[str, Any], list[Any]]):
    if isinstance(collection, list):
      for key, value in enumerate(collection):
        collection[key] = self.convert_to_object(value)
    elif isinstance(collection, dict):
      temp = models.MlModel()
      for key, value in collection.items():
        temp.__dict__[key] = self.convert_to_object(value)
      return temp

    return collection

  def first(self,
            iterable: Iterable[dict[str, Any]],
            key: str,
            value: str) -> dict[str, Any]:
    """Finds the dictionary in the list where the key matches value.

    Args:
        iterable: List of elements.
        key: Key to find.
        value: Value to compare.

    Returns:
      The matching dictionary.
    """
    return next(x for x in iterable if x[key] == value)


if __name__ == '__main__':
  absltest.main()
