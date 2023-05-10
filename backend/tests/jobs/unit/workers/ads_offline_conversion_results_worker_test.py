"""Tests for ads_offline_upload.AdsOfflineClickPageResultsWorker"""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from google.ads.googleads import client as ads_client_lib

from jobs.workers.ads import ads_offline_upload


class AdsOfflineClickPageResultsWorkerTest(parameterized.TestCase):
  def setUp(self):
    super().setUp()

    self.mock_loads_from_dict = self.enter_context(
      mock.patch.object(
        ads_client_lib.GoogleAdsClient, 'load_from_dict', autospec=True)
    )

  def test_creates_ad_client_for_service_account(self):
    """The ad conversion worker can be configured to create a service
    account client."""
    parameters = {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name',
      'google_ads_service_account_file': '/file/path',
    }
    worker = ads_offline_upload.AdsOfflineClickPageResultsWorker(
      parameters, 'pipeline_id', 'job_id'
    )
    worker._process_page_results(mock.MagicMock())

    expected = {'developer_token': 'token',
                'json_key_file_path': '/file/path'}
    self.mock_loads_from_dict.assert_called_with(expected)

  def test_creates_ad_client_for_refresh_token(self):
    """The ad conversion worker can be configured to create a refresh
     token client.
    """
    parameters = {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name',
      'google_ads_refresh_token': 'a_refresh_token',
      'client_id': 'a_client_id',
      'client_secret': 'a_client_secret',
    }
    worker = ads_offline_upload.AdsOfflineClickPageResultsWorker(
      parameters, 'pipeline_id', 'job_id'
    )
    worker._process_page_results(mock.MagicMock())

    expected = {
      'developer_token': 'token',
      'refresh_token': 'a_refresh_token',
      'client_id': 'a_client_id',
      'client_secret': 'a_client_secret',
    }
    self.mock_loads_from_dict.assert_called_with(expected)


if __name__ == '__main__':
  absltest.main()
