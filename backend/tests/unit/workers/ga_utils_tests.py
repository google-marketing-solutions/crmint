"""Tests for ga_utils."""

import json
import os
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google import auth
from google.auth import credentials
from googleapiclient import http

from jobs.workers.ga import ga_utils

DATA_DIR = os.path.join(os.path.dirname(__file__), '../../data')


def datafile(filename):
  return os.path.join(DATA_DIR, filename)


class GoogleAnalyticsUtilsTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    self.http_v3 = http.HttpMock(datafile('google_analytics_v3.json'),
                                 headers={'status': '200'})

  @parameterized.parameters(
      ('v3', 'https://analytics.googleapis.com/analytics/v3/'),
      ('v4', 'https://analyticsreporting.googleapis.com/'),
  )
  def test_get_client_with_version(self, version, api_base_url):
    mock_credentials = mock.create_autospec(
        credentials.Credentials, instance=True, spec_set=True)
    self.enter_context(
        mock.patch.object(
            auth,
            'default',
            autospec=True,
            spec_set=True,
            return_value=(mock_credentials, None)))
    client = ga_utils.get_client(version)
    self.assertEqual(client._baseUrl, api_base_url)

  def test_get_dataimport_upload_status_pending(self):
    # Response does not contain yet an upload item.
    response = {
        'kind': 'analytics#uploads',
        'totalResults': 1,
        'startIndex': 1,
        'itemsPerPage': 1000,
        'items': [],
    }
    request_builder = http.RequestMockBuilder(
        {'analytics.management.uploads.list': (None, json.dumps(response))})
    client = ga_utils.get_client(
        http=self.http_v3, request_builder=request_builder)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    upload_status = ga_utils.get_dataimport_upload_status(client, dataimport)
    self.assertEqual(upload_status, ga_utils.UploadStatus.PENDING)

  def test_get_dataimport_upload_status_completed(self):
    response = {
        'kind': 'analytics#uploads',
        'totalResults': 1,
        'startIndex': 1,
        'itemsPerPage': 1000,
        'items': [
            {
                'id': '5qan4As6S7WgAaQDTK25bg',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-23T10:00:54.822Z',
                'errors': [],
            }
        ],
    }
    request_builder = http.RequestMockBuilder(
        {'analytics.management.uploads.list': (None, json.dumps(response))})
    client = ga_utils.get_client(
        http=self.http_v3, request_builder=request_builder)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    upload_status = ga_utils.get_dataimport_upload_status(client, dataimport)
    self.assertEqual(upload_status, ga_utils.UploadStatus.COMPLETED)


if __name__ == '__main__':
  absltest.main()
