"""Tests for ga_audiences_updater."""

import os
import textwrap
from typing import Any, Dict, Iterable, Sequence
from unittest import mock

from absl.testing import absltest
from google.auth import credentials
from google.cloud import bigquery
from googleapiclient import http

from jobs.workers.ga import ga_audiences_updater
from jobs.workers.ga import ga_utils

DATA_DIR = os.path.join(os.path.dirname(__file__), '../../../data')

_SAMPLE_TEMPLATE = textwrap.dedent("""\
    {
      "name": "${name}",
      "linkedViews": ["${linked_view}"]
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


class GAAudiencesUpdaterTests(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.http_v3 = http.HttpMock(_datafile('google_analytics_v3.json'),
                                 headers={'status': '200'})

  def test_insert_and_updates_audiences(self):
    """Validates the logged messages sent for the end user."""
    request_builder = http.RequestMockBuilder({
        'analytics.management.remarketingAudience.list':
            (None,
             _read_datafile(
                 'analytics.management.remarketingAudience.list.page2.json')),
        'analytics.management.remarketingAudience.insert': (None, b'{}'),
        'analytics.management.remarketingAudience.patch': (None, b'{}'),
    })
    ga_client = ga_utils.get_client(
        'analytics', 'v3',
        http=self.http_v3, request_builder=request_builder)
    self.enter_context(
        mock.patch.object(
            ga_utils, 'get_client', autospec=True, return_value=ga_client))
    worker_inst = ga_audiences_updater.GAAudiencesUpdater(
        {
            'account_id': '123456',
            'property_id': 'UA-123456-7',
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
                    {'v': '12345678'},
                ]
            },
            {
                'f': [
                    {'v': 'Audience To Insert'},
                    {'v': '87654321'},
                ]
            },
        ],
    }

    bq_client = bigquery.Client(
        project='PROJECT', credentials=_make_credentials())
    table_schema = [
        bigquery.SchemaField('name', 'STRING'),
        bigquery.SchemaField('linked_view', 'STRING'),
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
            mock.call('Retrieved #2 audience configs from '
                      'BigQuery'),
            mock.call('Fetched #1 audiences from the GA '
                      'Property'),
            mock.call('Executing #2 operations to update the '
                      'state of GA with the audience configs from your '
                      'BigQuery'),
            mock.call('Updating existing audience for id: '
                      'PYDOUJQdSdGjAh6vERFpQQ'),
            mock.call('Inserting new audience'),
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )


if __name__ == '__main__':
  absltest.main()
