"""Tests for ads_offline_upload.AdsOfflineClickPageResultsWorker"""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from google.ads.googleads import client as ads_client_lib
from google.ads.googleads.v13.services.types import conversion_upload_service

from jobs.workers.bigquery import bq_to_ads_offline_click_conversion


JSON_TEMPLATE_PARAM_VALUE = """
  {
    "conversionEnvironment": "WEB",
    "gclid": "$gclid",
    "conversionAction": "$conversion_action",
    "conversionDateTime": "$conversion_date_time",
    "conversionValue": $conversion_value,
    "currencyCode": "$currency_code"
  }
"""


class AdsOfflineClickPageResultsWorkerTest(parameterized.TestCase):
  def setUp(self):
    super().setUp()

    self.test_api_request = (
      conversion_upload_service.UploadClickConversionsRequest()
    )
    self.setup_mocked_ad_client()

    self.patched_loads_from_dict = self.enter_context(
      mock.patch.object(
        ads_client_lib.GoogleAdsClient,
        'load_from_dict',
        autospec=True)
    )
    self.patched_loads_from_dict.return_value = self.mocked_ads_client

  def setup_mocked_ad_client(self):
    def return_get_type(value):
      if value == 'UploadClickConversionsRequest':
        return self.test_api_request
      else:
        return conversion_upload_service.ClickConversion()

    self.mocked_ads_client = mock.Mock(
      name="self.mocked_ads_client",
      spec=ads_client_lib.GoogleAdsClient,
    )
    self.mocked_ads_client.get_type.side_effect = return_get_type

  def _generate_default_params(self):
    return {
      'google_ads_developer_token': 'token',
      'google_ads_bigquery_conversions_table': 'bq_table_name',
      'google_ads_refresh_token': 'a_refresh_token',
      'client_id': 'a_client_id',
      'client_secret': 'a_client_secret',
      'customer_id': 'a_customer_id',
      'template': 'template_value',
    }

  @mock.patch('jobs.workers.worker.Worker.log_info')
  def test_creates_ad_client_for_refresh_token(self, _):
    """The ad conversion page results worker can be configured to create a
    refresh token client."""
    worker = bq_to_ads_offline_click_conversion.AdsOfflineClickPageResultsWorker(
      self._generate_default_params(), 1, 1
    )

    worker._process_page_results(mock.MagicMock())

    expected = {
      'developer_token': 'token',
      'refresh_token': 'a_refresh_token',
      'client_id': 'a_client_id',
      'client_secret': 'a_client_secret',
      'use_proto_plus': 'True'
    }
    self.patched_loads_from_dict.assert_called_with(expected)

  @mock.patch('jobs.workers.worker.Worker.log_info')
  def test_creates_upload_request_for_provided_customer_id(self, _):
    """The ad conversion page results worker sets the request customer ID to
    the provided customer ID."""
    worker = bq_to_ads_offline_click_conversion.AdsOfflineClickPageResultsWorker(
      self._generate_default_params(), 1, 1
    )

    worker._process_page_results(mock.MagicMock())

    self.assertEqual(self.test_api_request.customer_id, 'a_customer_id')

  @mock.patch('jobs.workers.worker.Worker.log_info')
  def test_creates_upload_request_for_provided_customer_id(self, _):
    """The ad conversion page results worker sets the request customer ID to
    the provided customer ID."""
    conversion_record_data = {
      'gclid': 'a_gclid',
      'conversion_value': '10.0',
      'conversion_date_time': '2023-05-01 10:10:10-08:00',
      'currency_code': 'USD',
      'conversion_action': '/a/conversion/action',
    }
    page_data = mock.MagicMock()
    page_data.num_items = 1
    page_data.__iter__.return_value = [conversion_record_data]

    params = self._generate_default_params()
    params['template'] = JSON_TEMPLATE_PARAM_VALUE

    worker = bq_to_ads_offline_click_conversion.AdsOfflineClickPageResultsWorker(
      params, 1, 1
    )
    worker._process_page_results(page_data)

    self.assertEqual(self.test_api_request.customer_id, 'a_customer_id')

  @mock.patch('jobs.workers.worker.Worker.log_info')
  def test_creates_upload_request_with_provided_conversion_data(self, _):
    """The ad conversion page results worker adds click conversions for each
    conversion row in the page dataset."""
    conversion_record_data_1 = {
      'gclid': 'a_gclid',
      'conversion_value': 10.0,
      'conversion_date_time': '2023-05-01 10:10:10-08:00',
      'currency_code': 'USD',
      'conversion_action': '/a/conversion/action',
    }
    conversion_record_data_2 = {
      'gclid': 'b_gclid',
      'conversion_value': 20.0,
      'conversion_date_time': '2023-05-10 10:10:10-08:00',
      'currency_code': 'USD',
      'conversion_action': '/b/conversion/action',
    }
    page_data = mock.MagicMock()
    page_data.num_items = 2
    page_data.__iter__.return_value = [
      conversion_record_data_1, conversion_record_data_2
    ]

    params = self._generate_default_params()
    params['template'] = JSON_TEMPLATE_PARAM_VALUE

    worker = bq_to_ads_offline_click_conversion.AdsOfflineClickPageResultsWorker(
      params, 1, 1
    )
    worker._process_page_results(page_data)

    expected_click_conversion_1 = conversion_upload_service.ClickConversion()
    expected_click_conversion_1.gclid = 'a_gclid'
    expected_click_conversion_1.conversion_value = 10.0
    expected_click_conversion_1.conversion_date_time = '2023-05-01 10:10:10-08:00'
    expected_click_conversion_1.currency_code = 'USD'
    expected_click_conversion_1.conversion_action = '/a/conversion/action'

    expected_click_conversion_2 = conversion_upload_service.ClickConversion()
    expected_click_conversion_2.gclid = 'b_gclid'
    expected_click_conversion_2.conversion_value = 20.0
    expected_click_conversion_2.conversion_date_time = '2023-05-10 10:10:10-08:00'
    expected_click_conversion_2.currency_code = 'USD'
    expected_click_conversion_2.conversion_action = '/b/conversion/action'

    expected_results = [
      expected_click_conversion_1, expected_click_conversion_2
    ]
    self.assertEqual(self.test_api_request.conversions, expected_results)


if __name__ == '__main__':
  absltest.main()
