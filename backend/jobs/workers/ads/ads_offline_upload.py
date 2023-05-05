# Copyright 2020 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workers to upload offline conversions to Google Ads."""
from typing import Dict, Any

from google.ads.googleads.client import GoogleAdsClient
from jobs.workers import worker

from jobs.workers.ads import ads_utils


DEVELOPER_TOKEN = 'google_ads_developer_token'
CONVERSIONS_BQ_TABLE = 'google_ads_bigquery_conversions_table'
SERVICE_ACCOUNT_FILE = 'google_ads_service_account_file'
REFRESH_TOKEN = 'google_ads_refresh_token'
CLIENT_ID = 'client_id'
CLIENT_SECRET = 'client_secret'


class _ConversionUploadConfigInfo():
  developer_token: str
  service_account_file: str
  refresh_token: str
  token_uri: str
  client_id: str
  client_secret: str
  conversion_bq_table: str

  def populate_from_params(self, params: dict[str, Any]) -> None:
    """Populates the configuration object from the provided dict."""
    self.developer_token = params.get(DEVELOPER_TOKEN, '')
    self.conversion_bq_table = params.get(CONVERSIONS_BQ_TABLE, '')

    self.service_account_file = params.get(SERVICE_ACCOUNT_FILE, '')
    self.refresh_token = params.get(REFRESH_TOKEN, '')
    self.client_id = params.get(CLIENT_ID, '')
    self.client_secret = params.get(CLIENT_SECRET, '')

    self._validate()

  def _validate(self) -> None:
    if not self.developer_token:
      raise ValueError('"google_ads_developer_token" is required and was not provided.')

    if not self.conversion_bq_table:
      raise ValueError('"google_ads_bigquery_conversions_table" is required and was not provided.')

    if not self.service_account_file and not self.refresh_token:
      raise ValueError('Provide either "google_ads_service_account_file"'
                       ' or "google_ads_refresh_token".')
    self._validate_ads_client_params()

  def _validate_ads_client_params(self):
    # If a service account file is provided, that's all we need for the service
    # OAuth server account flow.
    if self.service_account_file:
      return

    if not self.client_id:
      raise ValueError('"client_id" is required if an OAuth '
                       'refresh token is provided')

    if not self.client_secret:
      raise ValueError('"client_secret" is required if an OAuth '
                       'refresh token is provided')

  def is_service_account_auth(self) -> bool:
    """Is this config setup for service accounts?"""
    return bool(self.service_account_file)


class AdsOfflineClickConversionUploader(worker.Worker):
  """Worker for uploading offline click conversions into Google Ads.

  This worker supports uploading click-based offline conversions, where a
  GCLID is provided for each conversion action being uploaded.  The conversions
  with their GCLID's should be in a BigQuery table specified by the
  parameters.
  """

  PARAMS = [
    (CONVERSIONS_BQ_TABLE, 'string', True, '', 'Bigquery conversions table'),
  ]

  GLOBAL_SETTINGS = [
    DEVELOPER_TOKEN,
    SERVICE_ACCOUNT_FILE,
    REFRESH_TOKEN,
    CLIENT_ID,
    CLIENT_SECRET,
  ]

  def _execute(self) -> None:
    """Begin the processing and upload of offline click conversions."""
    self.config_data = _ConversionUploadConfigInfo()
    self.config_data.populate_from_params(self._params)

  #   ads_client = self._get_ads_client()
  #
  # def _get_ads_client(self) -> GoogleAdsClient:
  #   if self.config_data.is_service_account_auth():
  #     return ads_utils.get_ads_client_using_service_account(
  #       self.config_data.developer_token,
  #       self.config_data.service_account_file
  #     )
  #   else:
  #     return ads_utils.get_ads_client_using_refresh_tokens(
  #       self.config_data.developer_token,
  #       self.config_data.client_id,
  #       self.config_data.client_secret,
  #       self.config_data.refresh_token
  #     )
