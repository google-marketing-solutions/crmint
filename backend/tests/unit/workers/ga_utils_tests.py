"""Tests for ga_utils."""

import json
import os
import textwrap
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google import auth
from google.auth import credentials
from googleapiclient import discovery
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
                'id': '5qan4As6S7WgAa',
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

  @parameterized.named_parameters(
      ('Supports Universal Property ID format', 'UA-123456-7', '123456'),
      ('Supports GA4 Property ID format', 'GA-987654-32', '987654'),
  )
  def test_extract_accountid(self, property_id, expected_account_id):
    self.assertEqual(ga_utils.extract_accountid(property_id),
                     expected_account_id)

  def test_extract_accountid_raises_error_with_unsupported_format(self):
    with self.assertRaisesRegex(ValueError, 'Invalid Property ID'):
      ga_utils.extract_accountid('XY-123456-7')

  @parameterized.named_parameters(
      ('Deleted All', None, ['5qan4As6S7WgAa', 'qmcaotljicrpdw']),
      ('Keep most recent upload', 1,['5qan4As6S7WgAa']),
      ('Keep 2 most recent uploads', 2, []),
  )
  def test_delete_all_uploads(self, max_to_keep, expected_deleted_ids):
    response = {
        'kind': 'analytics#uploads',
        'totalResults': 1,
        'startIndex': 1,
        'itemsPerPage': 1000,
        'items': [
            {
                'id': 'qmcaotljicrpdw',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-24T10:00:54.822Z',
                'errors': [],
            },
            {
                'id': '5qan4As6S7WgAa',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-23T10:00:54.822Z',
                'errors': [],
            },
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
    deleted_ids = ga_utils.delete_oldest_uploads(
        client, dataimport, max_to_keep=max_to_keep)
    self.assertCountEqual(deleted_ids, expected_deleted_ids)

  @parameterized.named_parameters(
      ('Raises ValueError for negative value', -1),
      ('Raises ValueError for zero', 0),
  )
  def test_delete_all_uploads_with_bad_max_to_keep(self, max_to_keep):
    with self.assertRaisesRegex(ValueError,
                                'Invalid value for argument `max_to_keep`.'):
      ga_utils.delete_oldest_uploads(
          mock.ANY, mock.ANY, max_to_keep=max_to_keep)

  def test_upload_dataimport_without_progress_callback(self):
    ga_api_discovery_file = datafile('google_analytics_v3.json')
    with open(ga_api_discovery_file, 'rb') as f:
      ga_api_discovery_content = f.read()
    http_seq = http.HttpMockSequence(
        [
            # Location response, since it's a resumable upload
            ({'status': '200',
              'location': 'http://upload.example.com/1'}, b'{}'),
            # Upload by chunk responses
            ({'status': '308', 'range': 'bytes 0-9'}, b'{}'),
            ({'status': '308', 'range': 'bytes 0-19'}, b'{}'),
            ({'status': '200'}, b'{}'),
        ]
    )
    client = discovery.build_from_document(
        service=ga_api_discovery_content, http=http_seq)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    csv_file = self.create_tempfile(
        content=textwrap.dedent("""\
            UserId,Score
            123,0.5
            456,0.8"""))
    ga_utils.upload_dataimport(
        client,
        dataimport,
        csv_file.full_path,
        chunksize=10)  # Leads to 3 requests since our content is 28 bytes long.
    self.assertEmpty(http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')

  def test_upload_dataimport_with_progress_callback(self):
    ga_api_discovery_file = datafile('google_analytics_v3.json')
    with open(ga_api_discovery_file, 'rb') as f:
      ga_api_discovery_content = f.read()
    http_seq = http.HttpMockSequence(
        [
            # Location response, since it's a resumable upload
            ({'status': '200',
              'location': 'http://upload.example.com/1'}, b'{}'),
            # Upload by chunk responses
            ({'status': '308', 'range': 'bytes 0-9'}, b'{}'),
            ({'status': '308', 'range': 'bytes 0-19'}, b'{}'),
            ({'status': '200'}, b'{}'),
        ]
    )
    client = discovery.build_from_document(
        service=ga_api_discovery_content, http=http_seq)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    csv_file = self.create_tempfile(
        content=textwrap.dedent("""\
            UserId,Score
            123,0.5
            456,0.8"""))
    mock_progress_callback = mock.Mock()
    ga_utils.upload_dataimport(
        client,
        dataimport,
        csv_file.full_path,
        chunksize=10,  # Leads to 3 requests since our content is 28 bytes long.
        progress_callback=mock_progress_callback)
    self.assertEmpty(http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')
    self.assertSequenceEqual(
        (
            mock.call(0.3571),
            mock.call(0.7143),
            mock.call(1.0),
        ),
        mock_progress_callback.mock_calls,
    )


if __name__ == '__main__':
  absltest.main()
