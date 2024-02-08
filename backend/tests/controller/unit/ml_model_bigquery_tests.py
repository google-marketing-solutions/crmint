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


"""Tests for controller.ml_model.bigquery."""

import re
from typing import Any, Union
from unittest import mock

from absl.testing import absltest
from google.cloud.exceptions import NotFound

from controller.ml_model.bigquery import CustomClient


class TestClient(absltest.TestCase):

  @mock.patch('google.cloud.bigquery.Client.__init__')
  def setUp(self, init_mock: mock.Mock):
    super().setUp()
    init_mock.return_value = None
    self.client = CustomClient('US')
    self.client.project = 'test-project-id'

  @mock.patch('google.cloud.bigquery.Client.query')
  def test_get_analytics_variables(self, query_mock: mock.Mock):
    query_mock.return_value.result.return_value = self.convert_to_object([
        {
            'name': 'nm_5',
            'count': 22034,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'nm_4',
            'count': 10938,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'nm_3',
            'count': 784,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'nm_2',
            'count': 201,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'nm_1',
            'count': 77,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1,pvt_2',
        },
        {
            'name': 'nm_1',
            'count': 77,
            'parameter_key': 'pk_2',
            'parameter_value_type': 'pvt_3',
        },
        {
            'name': 'nm_2',
            'count': 201,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'nm_3',
            'count': 784,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'user_engagement',
            'count': 4578,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'nm_4',
            'count': 10938,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'nm_5',
            'count': 22034,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
        {
            'name': 'page_view',
            'count': 478458,
            'parameter_key': 'pk_1',
            'parameter_value_type': 'pvt_1',
        },
    ])

    variables = self.client.get_analytics_variables('test-ga4-project', 'test-ga4-dataset', 360, 30)
    _, args = query_mock.call_args

    # query check
    self.assertRegex(
        args['query'],
        r',[\s\n]+'.join([
            re.escape('FROM `test-ga4-project.test-ga4-dataset.events_*`')
        ]),
        'Query check failed. Missing project or analytics dataset name.')

    self.assertRegex(
        args['query'],
        r'[\s\n]+'.join([
            re.escape('FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), '
                      'INTERVAL 360 DAY)) AND'),
            re.escape('FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), '
                      'INTERVAL 30 DAY))')
        ]),
        'Query check failed. Incorrect start/end days.')

    # check name and result order is correct
    self.assertEqual(variables[0].name, 'nm_5')
    self.assertEqual(variables[1].name, 'nm_4')
    self.assertEqual(variables[2].name, 'nm_3')
    self.assertEqual(variables[3].name, 'nm_2')
    self.assertEqual(variables[4].name, 'nm_1')

    # check source
    for variable in variables:
      self.assertEqual(variable.source, 'GOOGLE_ANALYTICS')

    # check count
    self.assertEqual(variables[0].count, 22034)
    self.assertEqual(variables[1].count, 10938)
    self.assertEqual(variables[2].count, 784)
    self.assertEqual(variables[3].count, 201)
    self.assertEqual(variables[4].count, 77)

    # check parameter nesting
    parameters = variables[4].parameters
    self.assertLen(parameters, 2)
    self.assertEqual(parameters[0].key, 'pk_1')
    self.assertEqual(parameters[0].value_type, 'pvt_1,pvt_2')
    self.assertEqual(parameters[1].key, 'pk_2')
    self.assertEqual(parameters[1].value_type, 'pvt_3')

  @mock.patch('google.cloud.bigquery.Client.query')
  def test_get_analytics_variables_not_found(self, query_mock: mock.Mock):
    query_mock.side_effect = NotFound('not found.')
    variables = self.client.get_analytics_variables('test-ga4-project', 'test-ga4-dataset', 90, 30)
    self.assertEmpty(variables)

  @mock.patch('google.cloud.bigquery.Client.get_table')
  def test_get_first_party_variables(self, get_table_mock: mock.Mock):
    get_table_mock.return_value.schema = self.convert_to_object([
        {'name': 'col_1', 'field_type': 'type_1'},
        {'name': 'col_2', 'field_type': 'type_2'}
    ])

    variables = self.client.get_first_party_variables(
        'test-first-party-project', 'test-first-party-dataset', 'test-first-party-table')

    get_table_mock.assert_called_with('test-first-party-project.test-first-party-dataset.test-first-party-table')

    # check field names are returned
    self.assertEqual(variables[0].name, 'col_1')
    self.assertEqual(variables[1].name, 'col_2')

    # check source
    for variable in variables:
      self.assertEqual(variable.source, 'FIRST_PARTY')

    # check parameter nesting
    parameters = variables[0].parameters
    self.assertLen(parameters, 1)
    self.assertEqual(parameters[0].key, 'value')
    self.assertEqual(parameters[0].value_type, 'type_1')

  @mock.patch('google.cloud.bigquery.Client.get_table')
  def test_get_first_party_variables_not_found(self, get_table_mock: mock.Mock):
    get_table_mock.side_effect = NotFound('not found.')
    variables = self.client.get_first_party_variables(
        'test-first-party-project', 'test-first-party-dataset', 'test-first-party-table')
    self.assertEmpty(variables)

  def convert_to_object(self, collection: Union[dict[str, Any], list[Any]]):
    class TempObject:
      pass

    if isinstance(collection, list):
      for key, value in enumerate(collection):
        collection[key] = self.convert_to_object(value)
    elif isinstance(collection, dict):
      temp = TempObject()
      for key, value in collection.items():
        temp.__dict__[key] = self.convert_to_object(value)
      return temp

    return collection
