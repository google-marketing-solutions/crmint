"""Tests for ads_offline_upload.py"""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from jobs.workers.ads import ads_offline_upload


class AdsOfflineClickPageResultsWorkerTests(parameterized.TestCase):
  def setUp(self):
    super().setUp()

  @mock.patch('jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker._execute')
  def test_fails_if_required_params_not_provided(self, _):
    parameters = {}
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 0, 0
    )

    with self.assertRaises(ValueError) as err_context:
      worker._execute()

    self.assertIn('"template" is required.', str(err_context.exception))
    self.assertIn('"customer_id" is required.', str(err_context.exception))
    self.assertIn('"google_ads_developer_token" is required.',
                  str(err_context.exception))
    self.assertIn('"bq_project_id" is required.', str(err_context.exception))
    self.assertIn('"bq_dataset_id" is required.', str(err_context.exception))
    self.assertIn('"bq_table_id" is required.', str(err_context.exception))

  @mock.patch('jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker._execute')
  def test_either_service_account_or_refresh_token_is_required(self, _):
    """The Ad worker requires either a service account or refresh token."""
    parameters = {
      'google_ads_developer_token': 'token',
      'bq_project_id': '123',
      'bq_dataset_id': 'a_dataset',
      'bq_table_id': 'a_table',
      'template': 'a_template_string',
      'customer_id':  '123456'
    }
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    with self.assertRaises(ValueError) as err_context:
      worker._execute()

    self.assertIn(
      'Either "google_ads_service_account_file" or "google_ads_refresh_token"'
      ' are required',
      str(err_context.exception)
    )

  @mock.patch('jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker._execute')
  def test_can_client_params_are_required_if_refresh_token_provided(self, _):
    """The worker requires client ID and secret if a refresh token was
    provided.
    """
    parameters = {
      'google_ads_developer_token': 'token',
      'bq_project_id': '123',
      'bq_dataset_id': 'a_dataset',
      'bq_table_id': 'a_table',
      'template': 'a_template_string',
      'customer_id':  '123456',
      'google_ads_refresh_token': 'a_refresh_token'
    }

    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    with self.assertRaises(ValueError) as err_context:
      worker._execute()

    self.assertIn('"client_id" is required.', str(err_context.exception))
    self.assertIn('"client_secret" is required.', str(err_context.exception))

  @mock.patch('jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker._execute')
  def test_calls_parent_bq_batch_worker_to_start_execution(
    self,
    mocked_parent_execute
  ):
    """The Ad requires client ID and secret if a refresh token was provided."""
    parameters = {
      'google_ads_developer_token': 'token',
      'bq_project_id': '123',
      'bq_dataset_id': 'a_dataset',
      'bq_table_id': 'a_table',
      'template': 'a_template_string',
      'customer_id':  '123456',
      'google_ads_service_account_file': '/a/file/path'
    }

    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    worker._execute()

    mocked_parent_execute.assert_called()


if __name__ == '__main__':
  absltest.main()
