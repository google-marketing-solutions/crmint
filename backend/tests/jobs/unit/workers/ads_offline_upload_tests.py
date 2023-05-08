"""Tests for ads_offline_upload.py"""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from google.ads.googleads import client as ads_client_lib

from jobs.workers.ads import ads_offline_upload


class AdsOfflineClickConversionUploaderTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_loads_from_dict = self.enter_context(
      mock.patch.object(
        ads_client_lib.GoogleAdsClient, 'load_from_dict', autospec=True)
    )

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
    """The Ad worker fails when executed without required parameters.

    Given an Ads conversion uploader worker is instantiated
    And the developer token OR BQ table name haven't been provided
    When the worker is executed
    Then an exception is raised.
    """
    parameters = {
      'google_ads_developer_token': dev_token_value,
      'google_ads_bigquery_conversions_table': bq_table_value
    }
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    with self.assertRaises(ValueError) as err_context:
      worker._execute()
    self.assertIn(expected_err, str(err_context.exception))

  def test_either_service_account_or_refresh_token_is_required(self):
    """The Ad worker requires either a service account or refresh token.

    Given an Ads conversion uploader worker is instantiated
    And neither the service account file nor the refresh token were provided
    When the worker is executed
    Then an exception is raised.
    """
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

  def test_can_configure_with_only_service_account_file(self):
    """The Ad worker only requires a service account file to run.

    Given an Ads conversion uploader worker is instantiated
    And a service account file is provided
    When the worker is executed
    Then no exceptions are raised.
    """
    parameters = {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name',
      'google_ads_service_account_file': '/file/path',
    }
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    worker._execute()

  def test_creates_ad_client_for_service_account(self):
    """The ad conversion worker can be configured to create a service
    account client.

    Given an Ads conversion uploader worker is instantiated
    And a service account file is provided
    When the worker is executed
    It creates a Google Ads client configured for service account
      authentication.
    """
    parameters = {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name',
      'google_ads_service_account_file': '/file/path',
    }
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    worker._execute()

    expected = {'developer_token': 'token',
                'json_key_file_path': '/file/path',}
    self.mock_loads_from_dict.assert_called_with(expected)

  def test_creates_ad_client_for_refresh_token(self):
    """The ad conversion worker can be configured to create a refresh
     token client.

    Given an Ads conversion uploader worker is instantiated
    And a refresh token, client ID and client secret are provided
    When the worker is executed
    It creates a Google Ads client configured for refresh token authentication.
    """
    parameters = {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name',
      'google_ads_refresh_token': 'a_refresh_token',
      'client_id': 'a_client_id',
      'client_secret': 'a_client_secret',
    }
    worker = ads_offline_upload.AdsOfflineClickConversionUploader(
      parameters, 'pipeline_id', 'job_id'
    )
    worker._execute()

    expected = {
      'developer_token': 'token',
      'refresh_token': 'a_refresh_token',
      'client_id': 'a_client_id',
      'client_secret': 'a_client_secret',
    }
    self.mock_loads_from_dict.assert_called_with(expected)


if __name__ == '__main__':
  absltest.main()
