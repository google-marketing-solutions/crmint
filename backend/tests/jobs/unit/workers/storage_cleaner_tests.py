"""Tests for storage_cleaner."""

import datetime
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
import freezegun
from google.auth import credentials
from google.cloud import storage

from jobs.workers.storage import storage_cleaner


def _make_credentials():
  return mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)


class StorageCleanerTests(parameterized.TestCase):

  def _setup_blobs(self, fixed_last_update: datetime.datetime) -> None:
    mock_client = mock.create_autospec(
        storage.Client, instance=True, spec_set=True)
    self.enter_context(
        mock.patch.object(
            storage.Blob,
            'updated',
            new_callable=mock.PropertyMock,
            return_value=fixed_last_update))

    def _list_blobs(bucket):
      if bucket.name == 'bucket1':
        return [
            storage.Blob(
                'foo/file1.csv', storage.Bucket(mock_client, name='bucket1')),
            storage.Blob(
                'foo/file2.csv', storage.Bucket(mock_client, name='bucket1')),
            storage.Blob(
                'bar/file3.csv', storage.Bucket(mock_client, name='bucket1')),
        ]
      elif bucket.name == 'bucket2':
        return [
            storage.Blob(
                'foo/file1.csv', storage.Bucket(mock_client, name='bucket2')),
        ]
      else:
        raise ValueError(f'Unknown bucket: {bucket.name}')

    mock_client.list_blobs.side_effect = _list_blobs
    self.client = mock_client

  @parameterized.named_parameters(
      ('Naive update date', datetime.datetime(2022, 5, 1)),
      ('Aware update date',
       datetime.datetime(2022, 5, 1, tzinfo=datetime.timezone.utc)),
  )
  @freezegun.freeze_time('2022-05-15T00:00:00')
  def test_datetime_substraction(self, fixed_last_update):
    """Test no matter what the API is returning."""
    self._setup_blobs(fixed_last_update)
    worker_inst = storage_cleaner.StorageCleaner(
        {
            'file_uris': ['gs://bucket1/foo/file*.csv'],
            'expiration_days': 10,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    self.enter_context(
        mock.patch.object(
            storage, 'Client', autospec=True, return_value=self.client))
    self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    try:
      worker_inst.execute()
    except TypeError as e:
      self.fail(f'Failed with a type error: {e}')

  @parameterized.named_parameters(
      {'testcase_name': 'No match',
       'uri_patterns': ['gs://bucket1/nomatch/file*.csv'],
       'expiration_days': 10,
       'expected_logged_messages': []},
      {'testcase_name': 'Matching expired uris with wildcards',
       'uri_patterns': ['gs://bucket1/foo/file*.csv'],
       'expiration_days': 10,
       'expected_logged_messages':
           ['Deleted file at gs://bucket1/foo/file1.csv',
            'Deleted file at gs://bucket1/foo/file2.csv']},
      {'testcase_name': 'Matching non-expired uris without wildcards',
       'uri_patterns': ['gs://bucket1/foo/file*.csv'],
       'expiration_days': 20,
       'expected_logged_messages': []},
  )
  @freezegun.freeze_time('2022-05-15T00:00:00')
  def test_files_deletion(self,
                          uri_patterns,
                          expiration_days,
                          expected_logged_messages):
    self._setup_blobs(
        datetime.datetime(2022, 5, 1, tzinfo=datetime.timezone.utc))
    worker_inst = storage_cleaner.StorageCleaner(
        {
            'file_uris': uri_patterns,
            'expiration_days': expiration_days,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    self.enter_context(
        mock.patch.object(
            storage, 'Client', autospec=True, return_value=self.client))
    patched_logger = self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    worker_inst.execute()
    self.assertSequenceEqual(
        [
            mock.call(mock.ANY),
            *[mock.call(msg) for msg in expected_logged_messages],
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )


if __name__ == '__main__':
  absltest.main()
