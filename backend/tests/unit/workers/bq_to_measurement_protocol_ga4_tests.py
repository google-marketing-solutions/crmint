"""Tests for bq_to_measurement_protocol_ga4."""

import json
import textwrap
from typing import Any, Dict, Iterable, Sequence
from unittest import mock

from absl.testing import absltest
from google.auth import credentials
from google.cloud import bigquery
import requests

from jobs.workers import worker
from jobs.workers.bigquery import bq_to_measurement_protocol_ga4

_SAMPLE_WEB_TEMPLATE = textwrap.dedent("""\
    {
      "client_id": "${client_id}",
      "timestamp_micros": "${event_timestamp}",
      "nonPersonalizedAds": false,
      "events": [
        {
          "name": "post_score",
          "params": {
            "score": "${score}",
            "model_type": "${model_type}"
          }
        }
      ]
    }""")

_SAMPLE_APP_TEMPLATE = textwrap.dedent("""\
    {
      "app_instance_id": "${app_instance_id}",
      "timestamp_micros": "${event_timestamp}",
      "nonPersonalizedAds": false,
      "events": [
        {
          "name": "post_score",
          "params": {
            "score": "${score}",
            "model_type": "${model_type}"
          }
        }
      ]
    }""")


def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


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


class BQToMeasurementProtocolGA4Test(absltest.TestCase):

  def test_read_and_process_table_with_two_pages(self):
    worker_inst = bq_to_measurement_protocol_ga4.BQToMeasurementProtocolGA4(
        {
            'job_id': 'JOBID',
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'measurement_id': 'G-4713LA7M1F',
            'api_secret': 'xyz',
            'template': _SAMPLE_WEB_TEMPLATE,
            'mp_batch_size': 20,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery table read response.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/list#response-body
    api_response_page_1 = {
        'kind': 'bigquery#tableDataList',
        'totalRows': 2,
        'pageToken': 'abc',
        'rows': [
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 1234000000},
                    {'v': 0.9},
                    {'v': 'LTV v1'},
                ]
            },
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 1234000000},
                    {'v': 0.8},
                    {'v': 'LTV v1'},
                ]
            },
        ],
    }
    # Empties the `pageToken` for the 2nd page to simulate the end of the table.
    api_response_page_2 = api_response_page_1.copy()
    api_response_page_2['pageToken'] = ''

    bq_client = bigquery.Client(
        project='PROJECT', credentials=_make_credentials())
    table_schema = [
        bigquery.SchemaField('tracking_id', 'STRING'),
        bigquery.SchemaField('client_id', 'STRING'),
        bigquery.SchemaField('event_timestamp', 'TIMESTAMP'),
        bigquery.SchemaField('score', 'FLOAT'),
        bigquery.SchemaField('model_type', 'STRING'),
    ]
    _use_query_results(bq_client,
                       table_schema,
                       [api_response_page_1, api_response_page_2])

    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    self.enter_context(
        mock.patch.object(
            worker_inst, '_get_client', autospec=True, return_value=bq_client))
    # Limits the enqueuing to 1 processing tasks and the batch size to 100
    worker_inst.BQ_BATCH_SIZE = 100
    worker_inst.MAX_ENQUEUED_JOBS = 1
    enqueued_workers = worker_inst.execute()
    self.assertLen(enqueued_workers, 2)
    with self.subTest('Enqueued one processing task worker'):
      expected_params = worker_inst._params.copy()
      expected_params['bq_batch_size'] = 100
      self.assertEqual(
          enqueued_workers[0],
          ('BQToMeasurementProtocolProcessorGA4', expected_params, 0))
    with self.subTest('Enqueued the next page worker'):
      expected_params = worker_inst._params.copy()
      expected_params['bq_page_token'] = 'abc'
      self.assertEqual(
          enqueued_workers[1],
          ('BQToMeasurementProtocolGA4', expected_params, 0))


class TestBQToMeasurementProtocolProcessor(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self._bq_client = bigquery.Client(
        project='PROJECT', credentials=_make_credentials())
    self.enter_context(
        mock.patch.object(
            bq_to_measurement_protocol_ga4.BQToMeasurementProtocolProcessorGA4,
            '_get_client',
            autospec=True,
            return_value=self._bq_client))
    self._patched_post = self.enter_context(
        mock.patch.object(requests, 'post', autospec=True))

  def test_debug_flag_sends_data_to_debug_endpoint(self):
    worker_inst = bq_to_measurement_protocol_ga4.BQToMeasurementProtocolProcessorGA4(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'bq_batch_size': 10,
            'mp_batch_size': 20,
            'measurement_id': 'G-4713LA7M1F',
            'api_secret': 'xyz',
            'template': _SAMPLE_WEB_TEMPLATE,
            'debug': True,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery table read response.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/list#response-body
    api_response = {
        'kind': 'bigquery#tableDataList',
        'totalRows': 1,
        'rows': [
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 1234000000},
                    {'v': 0.8},
                    {'v': 'LTV v1'},
                ]
            },
        ],
    }
    table_schema = [
        bigquery.SchemaField('tracking_id', 'STRING'),
        bigquery.SchemaField('client_id', 'STRING'),
        bigquery.SchemaField('event_timestamp', 'INTEGER'),
        bigquery.SchemaField('score', 'FLOAT'),
        bigquery.SchemaField('model_type', 'STRING'),
    ]
    _use_query_results(self._bq_client, table_schema, [api_response])

    post_response = requests.Response()
    post_response.status_code = 200
    post_response._content = b"""
        {
            "validationMessages": [
                {"description": "There is a formatting error"}
            ]
        }"""
    self._patched_post.return_value = post_response

    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    patched_warn = self.enter_context(
        mock.patch.object(worker_inst, 'log_warn', autospec=True))
    worker_inst._execute()
    self._patched_post.assert_called_once_with(
        'https://www.google-analytics.com/debug/mp/collect?measurement_id=G-4713LA7M1F&api_secret=xyz',
        data=json.dumps({
            'client_id': '35009a79-1a05-49d7-b876-2b884d0f825b',
            'timestamp_micros': '1234000000',
            'nonPersonalizedAds': False,
            'events': [{
                'name': 'post_score',
                'params': {
                    'score': '0.8',
                    'model_type': 'LTV v1',
                }
            }]
        }),
        headers={'content-type': 'application/json'})
    self.assertIn('There is a formatting error', patched_warn.call_args[0][0])

  def test_success_with_one_post_request(self):
    worker_inst = bq_to_measurement_protocol_ga4.BQToMeasurementProtocolProcessorGA4(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'bq_batch_size': 10,
            'mp_batch_size': 20,
            'measurement_id': 'G-4713LA7M1F',
            'api_secret': 'xyz',
            'template': _SAMPLE_WEB_TEMPLATE,
            'debug': False,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery table read response.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/list#response-body
    api_response = {
        'kind': 'bigquery#tableDataList',
        'totalRows': 2,
        'rows': [
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 1234000000},
                    {'v': 0.9},
                    {'v': 'LTV v1'},
                ]
            },
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 1234000000},
                    {'v': 0.8},
                    {'v': 'LTV v1'},
                ]
            }
        ],
    }
    table_schema = [
        bigquery.SchemaField('tracking_id', 'STRING'),
        bigquery.SchemaField('client_id', 'STRING'),
        bigquery.SchemaField('event_timestamp', 'TIMESTAMP'),
        bigquery.SchemaField('score', 'FLOAT'),
        bigquery.SchemaField('model_type', 'STRING'),
    ]
    _use_query_results(self._bq_client, table_schema, [api_response])

    post_response = requests.Response()
    post_response.status_code = 204
    self._patched_post.return_value = post_response

    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    worker_inst._execute()
    self.assertEqual(self._patched_post.call_count, 2)
    self._patched_post.assert_called_with(
        'https://www.google-analytics.com/mp/collect?measurement_id=G-4713LA7M1F&api_secret=xyz',
        data=json.dumps({
            'client_id': '35009a79-1a05-49d7-b876-2b884d0f825b',
            'timestamp_micros': '1970-01-01 00:20:34+00:00',
            'nonPersonalizedAds': False,
            'events': [{
                'name': 'post_score',
                'params': {
                    'score': '0.8',
                    'model_type': 'LTV v1',
                }
            }]
        }),
        headers={'content-type': 'application/json'})

  def test_success_with_one_post_request_android(self):
    worker_inst = bq_to_measurement_protocol_ga4.BQToMeasurementProtocolProcessorGA4(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'bq_batch_size': 10,
            'mp_batch_size': 20,
            'measurement_id': '1:1234567890:android:321abc456def7890',
            'api_secret': 'xyz',
            'template': _SAMPLE_APP_TEMPLATE,
            'debug': False,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery table read response.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/list#response-body
    api_response = {
        'kind': 'bigquery#tableDataList',
        'totalRows': 2,
        'rows': [
            {
                'f': [
                    {'v': 'AE9C7A5E358F2E0E0E90E4B8DD67AE76'},
                    {'v': 1234000000},
                    {'v': 0.9},
                    {'v': 'LTV v1'},
                ]
            },
            {
                'f': [
                    {'v': 'AE9C7A5E358F2E0E0E90E4B8DD67AE76'},
                    {'v': 1234000000},
                    {'v': 0.8},
                    {'v': 'LTV v1'},
                ]
            }
        ],
    }
    table_schema = [
        bigquery.SchemaField('app_instance_id', 'STRING'),
        bigquery.SchemaField('event_timestamp', 'TIMESTAMP'),
        bigquery.SchemaField('score', 'FLOAT'),
        bigquery.SchemaField('model_type', 'STRING'),
    ]
    _use_query_results(self._bq_client, table_schema, [api_response])

    post_response = requests.Response()
    post_response.status_code = 204
    self._patched_post.return_value = post_response

    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    worker_inst._execute()
    self.assertEqual(self._patched_post.call_count, 2)
    self._patched_post.assert_called_with(
        'https://www.google-analytics.com/mp/collect?firebase_app_id=1%3A1234567890%3Aandroid%3A321abc456def7890&api_secret=xyz',
        data=json.dumps({
            'app_instance_id': 'AE9C7A5E358F2E0E0E90E4B8DD67AE76',
            'timestamp_micros': '1970-01-01 00:20:34+00:00',
            'nonPersonalizedAds': False,
            'events': [{
                'name': 'post_score',
                'params': {
                    'score': '0.8',
                    'model_type': 'LTV v1',
                }
            }]
        }),
        headers={'content-type': 'application/json'})

  def test_success_with_one_post_request_ios(self):
    worker_inst = bq_to_measurement_protocol_ga4.BQToMeasurementProtocolProcessorGA4(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'bq_batch_size': 10,
            'mp_batch_size': 20,
            'measurement_id': '1:1234567890:ios:321abc456def7890',
            'api_secret': 'xyz',
            'template': _SAMPLE_APP_TEMPLATE,
            'debug': False,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery table read response.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/list#response-body
    api_response = {
        'kind': 'bigquery#tableDataList',
        'totalRows': 2,
        'rows': [
            {
                'f': [
                    {'v': 'AE9C7A5E358F2E0E0E90E4B8DD67AE76'},
                    {'v': 1234000000},
                    {'v': 0.9},
                    {'v': 'LTV v1'},
                ]
            },
            {
                'f': [
                    {'v': 'AE9C7A5E358F2E0E0E90E4B8DD67AE76'},
                    {'v': 1234000000},
                    {'v': 0.8},
                    {'v': 'LTV v1'},
                ]
            }
        ],
    }
    table_schema = [
        bigquery.SchemaField('app_instance_id', 'STRING'),
        bigquery.SchemaField('event_timestamp', 'TIMESTAMP'),
        bigquery.SchemaField('score', 'FLOAT'),
        bigquery.SchemaField('model_type', 'STRING'),
    ]
    _use_query_results(self._bq_client, table_schema, [api_response])

    post_response = requests.Response()
    post_response.status_code = 204
    self._patched_post.return_value = post_response

    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    worker_inst._execute()
    self.assertEqual(self._patched_post.call_count, 2)
    self._patched_post.assert_called_with(
        'https://www.google-analytics.com/mp/collect?firebase_app_id=1%3A1234567890%3Aios%3A321abc456def7890&api_secret=xyz',
        data=json.dumps({
            'app_instance_id': 'AE9C7A5E358F2E0E0E90E4B8DD67AE76',
            'timestamp_micros': '1970-01-01 00:20:34+00:00',
            'nonPersonalizedAds': False,
            'events': [{
                'name': 'post_score',
                'params': {
                    'score': '0.8',
                    'model_type': 'LTV v1',
                }
            }]
        }),
        headers={'content-type': 'application/json'})

  def test_log_exception_if_http_fails(self):
    worker_inst = bq_to_measurement_protocol_ga4.BQToMeasurementProtocolProcessorGA4(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'bq_batch_size': 10,
            'mp_batch_size': 20,
            'measurement_id': 'G-4713LA7M1F',
            'api_secret': 'xyz',
            'template': _SAMPLE_WEB_TEMPLATE,
            'debug': False,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery table read response.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/list#response-body
    api_response = {
        'kind': 'bigquery#tableDataList',
        'totalRows': 2,
        'rows': [
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 1234000000},
                    {'v': 0},
                    {'v': 'LTV v1'},
                ]
            }
        ],
    }
    table_schema = [
        bigquery.SchemaField('tracking_id', 'STRING'),
        bigquery.SchemaField('client_id', 'STRING'),
        bigquery.SchemaField('event_timestamp', 'TIMESTAMP'),
        bigquery.SchemaField('score', 'FLOAT'),
        bigquery.SchemaField('model_type', 'STRING'),
    ]
    _use_query_results(self._bq_client, table_schema, [api_response])

    post_response = requests.Response()
    post_response.status_code = 400
    self._patched_post.return_value = post_response

    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    with self.assertRaisesRegex(worker.WorkerException,
                                'Failed to send event with status code .*'):
      worker_inst._execute()


if __name__ == '__main__':
  absltest.main()
