"""Tests for ads_offline_upload.py"""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from google.ads.googleads import client as ads_client_lib

from jobs.workers.ads import ads_offline_upload


class AdsOfflineClickPageResultsWorkerTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()

  @parameterized.parameters(
    {'dev_token_value': '',
     'bq_table_value': '',
     'expected_err': '"google_ads_developer_token" is required and was not provided.',},
    {'dev_token_value': 'token',
     'bq_table_value': '',
     'expected_err': '"google_ads_bigquery_conversions_table" is required and was not provided.',},
  )
  def test_fails_if_required_params_not_provided(
    self,
    dev_token_value,
    bq_table_value,
    expected_err
  ):
    parameters = {
      'google_ads_developer_token': dev_token_value,
      'google_ads_bigquery_conversions_table': bq_table_value
    }
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 0, 0
    )

    with mock.patch(
      'jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker._execute'
    ) as _:
      with self.assertRaises(ValueError) as err_context:
        worker._execute()
      self.assertIn(expected_err, str(err_context.exception))

  @mock.patch('jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker._execute')
  def test_either_service_account_or_refresh_token_is_required(self, _):
    """The Ad worker requires either a service account or refresh token."""
    parameters = {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name'
    }
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    with self.assertRaises(ValueError) as err_context:
      worker._execute()

    self.assertEqual(
      'Provide either "google_ads_service_account_file"'
      ' or "google_ads_refresh_token".',
      str(err_context.exception))

  @mock.patch('jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker._execute')
  def test_can_configure_with_only_service_account_file(self, _):
    """The Ad worker only requires a service account file to run."""
    parameters = {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name',
      'google_ads_service_account_file': '/file/path',
    }
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    worker._execute()

  @parameterized.parameters(
    {'client_id_value': '',
     'client_secret_value': '',
     'expected_err': '"client_id" is required if an OAuth refresh token is provided'},
    {'client_id_value': 'a_client_id',
     'client_secret_value': '',
     'expected_err': '"client_secret" is required if an OAuth refresh token is provided'},
  )
  def test_can_client_params_are_required_if_refresh_token_provided(
    self,
    client_id_value,
    client_secret_value,
    expected_err
  ):
    """The Ad requires client ID and secret if a refresh token was provided."""
    parameters = {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name',
      'google_ads_refresh_token': 'a_refresh_token',
      'client_id': client_id_value,
      'client_secret': client_secret_value
    }

    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    with mock.patch(
      'jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker._execute'
    ) as _:
      with self.assertRaises(ValueError) as err_context:
        worker._execute()
      self.assertIn(expected_err, str(err_context.exception))


if __name__ == '__main__':
  absltest.main()
