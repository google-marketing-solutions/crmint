"""Tests for ga_audiences_updater_ga4."""

import os
import textwrap
from typing import Any, Dict, Iterable, Sequence
from unittest import mock

from absl.testing import absltest
from google.auth import credentials
from google.cloud import bigquery
from googleapiclient import http

from common import crmint_logging
from jobs.workers.ga import ga_audiences_updater_ga4
from jobs.workers.ga import ga_utils

DATA_DIR = os.path.join(os.path.dirname(__file__), '../../../data')

_SAMPLE_TEMPLATE = textwrap.dedent("""\
    {
      "displayName": "${display_name}",
      "description": "${description}",
      "membershipDurationDays": 30,
      "filterClauses": [
        {
          "clauseType": "INCLUDE",
          "simpleFilter": {
            "scope": "AUDIENCE_FILTER_SCOPE_ACROSS_ALL_SESSIONS",
            "filterExpression": {
              "andGroup": {
                "filterExpressions": [
                  {
                    "orGroup": {
                      "filterExpressions": [
                        {
                          "eventFilter": {
                            "eventName": "${event_name}",
                            "eventParameterFilterExpression": {
                              "andGroup": {
                                "filterExpressions": [
                                  {
                                    "orGroup": {
                                      "filterExpressions": [
                                        {
                                          "dimensionOrMetricFilter": {
                                            "fieldName": "value",
                                            "numericFilter": {
                                              "operation": "GREATER_THAN",
                                              "value": {
                                                "doubleValue": ${greater_than}
                                              }
                                            }
                                          }
                                        }
                                      ]
                                    }
                                  }
                                ]
                              }
                            }
                          }
                        }
                      ]
                    }
                  },
                  {
                    "orGroup": {
                      "filterExpressions": [
                        {
                          "eventFilter": {
                            "eventName": "${event_name}",
                            "eventParameterFilterExpression": {
                              "andGroup": {
                                "filterExpressions": [
                                  {
                                    "orGroup": {
                                      "filterExpressions": [
                                        {
                                          "dimensionOrMetricFilter": {
                                            "fieldName": "value",
                                            "numericFilter": {
                                              "operation": "LESS_THAN",
                                              "value": {
                                                "doubleValue": ${less_than}
                                              }
                                            }
                                          }
                                        }
                                      ]
                                    }
                                  }
                                ]
                              }
                            }
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        }
      ]
    }""")


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


def _read_datafile(filename):
  with open(_datafile(filename), 'rb') as f:
    content = f.read()
  return content


def _make_credentials():
  return mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)


def _use_query_results(bq_client: bigquery.Client,
                       schema: Sequence[bigquery.SchemaField],
                       stub_json_responses: Iterable[Dict[str, Any]]) -> None:
  """Configures the given BigQuery client to use stubed results."""
  mock_dataset = mock.create_autospec(
      bigquery.Dataset, instance=True, spec_set=True)
  mock_table = mock.create_autospec(
      bigquery.Table, instance=True, spec_set=True)
  mock_table.schema = schema
  mock_dataset.table.return_value = mock_table
  bq_client._connection = mock.MagicMock()
  bq_client._connection.api_request.side_effect = stub_json_responses
  bq_client.get_dataset = mock.Mock(return_value=mock_dataset)
  bq_client.get_table = mock.Mock(return_value=mock_table)


class GA4AudiencesUpdaterTests(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.http_v1alpha = http.HttpMock(
        _datafile('google_analytics_admin_v1alpha.json'),
        headers={'status': '200'})
    self.patched_log_message = self.enter_context(
        mock.patch.object(crmint_logging, 'log_global_message', autospec=True))

  def test_insert_and_updates_audiences(self):
    """Validates the logged messages sent for the end user."""
    request_builder = http.RequestMockBuilder({
        'analyticsadmin.properties.audiences.list':
            (None,
             _read_datafile(
                 'analyticsadmin.properties.audiences.list.page2.json')),
        'analyticsadmin.properties.audiences.create': (None, b'{}'),
        'analyticsadmin.properties.audiences.patch': (None, b'{}'),
    })
    ga_client = ga_utils.get_client(
        'analyticsadmin', 'v1alpha',
        http=self.http_v1alpha, request_builder=request_builder)
    self.enter_context(
        mock.patch.object(
            ga_utils, 'get_client', autospec=True, return_value=ga_client))
    worker_inst = ga_audiences_updater_ga4.GA4AudiencesUpdater(
        {
            'ga_property_id': '123456',
            'bq_project_id': 'PROJECT',
            'bq_dataset_id': 'DATASET',
            'bq_table_id': 'TABLE',
            'bq_dataset_location': 'EU',
            'template': _SAMPLE_TEMPLATE,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery table read response.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/list#response-body
    bq_api_response = {
        'kind': 'bigquery#tableDataList',
        'totalRows': 2,
        'rows': [
            {
                'f': [
                    {'v': 'All Users'},
                    {'v': 'List of all users'},
                    {'v': 'conv1_name'},
                    {'v': 0.1},
                    {'v': 0.4},
                ]
            },
            {
                'f': [
                    {'v': 'Audience To Insert'},
                    {'v': 'List of users we want to add'},
                    {'v': 'conv2_name'},
                    {'v': 0.2},
                    {'v': 0.8},
                ]
            },
        ],
    }

    bq_client = bigquery.Client(
        project='PROJECT', credentials=_make_credentials())
    table_schema = [
        bigquery.SchemaField('display_name', 'STRING'),
        bigquery.SchemaField('description', 'STRING'),
        bigquery.SchemaField('event_name', 'STRING'),
        bigquery.SchemaField('greater_than', 'FLOAT64'),
        bigquery.SchemaField('less_than', 'FLOAT64')
    ]
    _use_query_results(bq_client, table_schema, [bq_api_response])

    self.enter_context(
        mock.patch.object(
            worker_inst, '_get_client', autospec=True, return_value=bq_client))
    patched_logger = self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    worker_inst.execute()
    self.assertSequenceEqual(
        [
            mock.call(mock.ANY),
            mock.call('Retrieved #2 audience configs from BigQuery'),
            mock.call('Fetched #2 audiences from the GA4 Property'),
            mock.call('Executing #2 operations to update the state of '
                      'GA4 with the audience configs from your BigQuery'),
            mock.call('Updating existing audience for name: All Users and '
                      'resource: properties/312213553/audiences/3951191362'),
            mock.call('Inserting new audience'),
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )


if __name__ == '__main__':
  absltest.main()
