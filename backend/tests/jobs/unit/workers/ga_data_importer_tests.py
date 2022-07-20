"""Tests for ga_data_importer."""

import json
import os
from unittest import mock

from absl.testing import absltest
from google.auth import credentials
from google.cloud import storage
from googleapiclient import discovery
from googleapiclient import http

from jobs.workers.ga import ga_data_importer
from jobs.workers.ga import ga_utils

DATA_DIR = os.path.join(os.path.dirname(__file__), '../../../data')


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


def _make_credentials():
  return mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)


class GADataImporterTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    gcs_client = storage.Client(project='PROJECT',
                                credentials=_make_credentials())
    self.enter_context(
        mock.patch.object(
            storage, 'Client', autospec=True, return_value=gcs_client))
    self.enter_context(
        mock.patch.object(storage.Blob, 'reload', autospec=True))

    def _write_content(unused_blob, file_obj, *unused_args, **unused_kwargs):
      file_obj.write(b'hello world!')

    self.enter_context(
        mock.patch.object(
            gcs_client, 'download_blob_to_file', side_effect=_write_content))

  def _setup_ga_client_with_responses(self, http_responses):
    ga_api_discovery_file = _datafile('google_analytics_v3.json')
    with open(ga_api_discovery_file, 'rb') as f:
      ga_api_discovery_content = f.read()
    http_seq = http.HttpMockSequence(http_responses)
    ga_client = discovery.build_from_document(
        service=ga_api_discovery_content, http=http_seq)
    self.enter_context(
        mock.patch.object(
            ga_utils, 'get_client', autospec=True, return_value=ga_client))
    self.http_seq = http_seq

  def test_keep_all_uploads_and_upload_dataimport(self):
    """Validates the logged messages sent for the end user."""
    self._setup_ga_client_with_responses([
        # 1. Call to analytics.management.uploads.uploadData
        # Location response, since it's a resumable upload
        ({'status': '200',
          'location': 'http://upload.example.com/1'}, b'{}'),
        # Upload in one chunk (since our file is less than 1MB)
        ({'status': '200'}, b'{}'),
    ])
    worker_inst = ga_data_importer.GADataImporter(
        {
            'csv_uri': 'gs://mybucket/foo/bar.csv',
            'account_id': '123456',
            'property_id': 'UA-123456-7',
            'dataset_id': 'sLj2CuBTDFy6CedBJwahFt',
            'max_uploads': None,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    patched_logger = self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    worker_inst.execute()
    self.assertEmpty(self.http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')
    self.assertSequenceEqual(
        [
            mock.call(mock.ANY),
            mock.call('Kept all uploads'),
            mock.call('Downloaded file from Cloud Storage to App Engine'),
            mock.call('Uploaded 100%'),
            mock.call('Successfully uploaded data import to Google Analytics'),
            mock.call('Cleaned up the downloaded file'),
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )

  def test_deleted_old_uploads_and_upload_dataimport(self):
    """Validates the logged messages sent for the end user."""
    # Response with two uploads, will generate 1 deleted id later.
    upload_list_response = {
        'kind': 'analytics#uploads',
        'totalResults': 1,
        'startIndex': 1,
        'itemsPerPage': 1000,
        'items': [
            {
                'id': 'qmcaotljicrpdwafcwiukh',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-24T10:00:54.822Z',
                'errors': [],
            },
            {
                'id': '5qan4As6S7WgAaQDTK25bg',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-23T10:00:54.822Z',
                'errors': [],
            },
        ],
    }
    self._setup_ga_client_with_responses([
        # 1. Call to analytics.management.uploads.list
        ({'status': '200'}, json.dumps(upload_list_response)),

        # 2. Call to analytics.management.uploads.deleteUploadData
        ({'status': '200'}, b'{}'),

        # 3. Call to analytics.management.uploads.uploadData
        # Location response, since it's a resumable upload
        ({'status': '200',
          'location': 'http://upload.example.com/1'}, b'{}'),
        # Upload in one chunk (since our file is less than 1MB)
        ({'status': '200'}, b'{}'),
    ])
    worker_inst = ga_data_importer.GADataImporter(
        {
            'csv_uri': 'gs://mybucket/foo/bar.csv',
            'account_id': '123456',
            'property_id': 'UA-123456-7',
            'dataset_id': 'sLj2CuBTDFy6CedBJwahFt',
            'max_uploads': 2,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    patched_logger = self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    worker_inst.execute()
    self.assertEmpty(self.http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')
    self.assertSequenceEqual(
        [
            mock.call(mock.ANY),
            mock.call('Deleted oldest upload(s) '
                      'for ids: [\'5qan4As6S7WgAaQDTK25bg\']'),
            mock.call('Downloaded file from Cloud Storage to App Engine'),
            mock.call('Uploaded 100%'),
            mock.call('Successfully uploaded data import to Google Analytics'),
            mock.call('Cleaned up the downloaded file'),
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )

  def test_deleted_all_uploads_and_upload_dataimport(self):
    """Validates the logged messages sent for the end user."""
    # Response with two uploads, will generate 1 deleted id later.
    upload_list_response = {
        'kind': 'analytics#uploads',
        'totalResults': 1,
        'startIndex': 1,
        'itemsPerPage': 1000,
        'items': [
            {
                'id': 'qmcaotljicrpdwafcwiukh',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-24T10:00:54.822Z',
                'errors': [],
            },
            {
                'id': '5qan4As6S7WgAaQDTK25bg',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-23T10:00:54.822Z',
                'errors': [],
            },
        ],
    }
    self._setup_ga_client_with_responses([
        # 1. Call to analytics.management.uploads.list
        ({'status': '200'}, json.dumps(upload_list_response)),

        # 2. Call to analytics.management.uploads.deleteUploadData
        ({'status': '200'}, b'{}'),

        # 3. Call to analytics.management.uploads.uploadData
        # Location response, since it's a resumable upload
        ({'status': '200',
          'location': 'http://upload.example.com/1'}, b'{}'),
        # Upload in one chunk (since our file is less than 1MB)
        ({'status': '200'}, b'{}'),
    ])
    worker_inst = ga_data_importer.GADataImporter(
        {
            'csv_uri': 'gs://mybucket/foo/bar.csv',
            'account_id': '123456',
            'property_id': 'UA-123456-7',
            'dataset_id': 'sLj2CuBTDFy6CedBJwahFt',
            'max_uploads': 1,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    patched_logger = self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    worker_inst.execute()
    self.assertEmpty(self.http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')
    self.assertSequenceEqual(
        [
            mock.call(mock.ANY),
            mock.call('Deleted all existing uploads for ids: '
                      '[\'5qan4As6S7WgAaQDTK25bg\', '
                      '\'qmcaotljicrpdwafcwiukh\']'),
            mock.call('Downloaded file from Cloud Storage to App Engine'),
            mock.call('Uploaded 100%'),
            mock.call('Successfully uploaded data import to Google Analytics'),
            mock.call('Cleaned up the downloaded file'),
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )


if __name__ == '__main__':
  absltest.main()
