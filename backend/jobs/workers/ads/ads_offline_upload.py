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
from typing import Any

from google.ads.googleads import client
from google.api_core import page_iterator

from jobs.workers.bigquery import bq_batch_worker


DEVELOPER_TOKEN = 'google_ads_developer_token'
CONVERSIONS_BQ_TABLE = 'google_ads_bigquery_conversions_table'
SERVICE_ACCOUNT_FILE = 'google_ads_service_account_file'
REFRESH_TOKEN = 'google_ads_refresh_token'
CLIENT_ID = 'client_id'
CLIENT_SECRET = 'client_secret'


class AdsOfflineClickConversionUploader(bq_batch_worker.BQBatchDataWorker):
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

  def _validate_params(self) -> None:
    if not self._params.get(DEVELOPER_TOKEN, None):
      raise ValueError('"google_ads_developer_token" is required and was not provided.')

    if not self._params.get(CONVERSIONS_BQ_TABLE, None):
      raise ValueError('"google_ads_bigquery_conversions_table" is required and was not provided.')

    if not self._params.get(SERVICE_ACCOUNT_FILE, None) and not self._params.get(REFRESH_TOKEN, None):
      raise ValueError('Provide either "google_ads_service_account_file"'
                       ' or "google_ads_refresh_token".')
    self._validate_ads_client_params()

  def _validate_ads_client_params(self):
    # If a service account file is provided, that's all we need for the service
    # OAuth server account flow.
    if self._params.get(SERVICE_ACCOUNT_FILE, None):
      return

    if not self._params.get(CLIENT_ID, None) :
      raise ValueError('"client_id" is required if an OAuth '
                       'refresh token is provided')

    if not self._params.get(CLIENT_SECRET, None) :
      raise ValueError('"client_secret" is required if an OAuth '
                       'refresh token is provided')

  def _execute(self) -> None:
    """Begin the processing and upload of offline click conversions."""
    self._validate_params()
    self._params[bq_batch_worker.BQ_TABLE_TO_PROCESS_PARAM] = \
      self._params[CONVERSIONS_BQ_TABLE]

    super()._execute()

  def _get_sub_worker_name(self) -> str:
    return AdsOfflineClickPageResultsWorker.__class__.__name__


class AdsOfflineClickPageResultsWorker(bq_batch_worker.TablePageResultsProcessorWorker):
  """"""

  def _process_page_results(self, page_data: page_iterator.Page) -> None:
    ads_client = self._get_ads_client()

  def _get_ads_client(self) -> client.GoogleAdsClient:
    client_params = {'developer_token': self._params[DEVELOPER_TOKEN]}

    if SERVICE_ACCOUNT_FILE in self._params:
      client_params['json_key_file_path'] = self._params[SERVICE_ACCOUNT_FILE]
    else:
      client_params['client_id'] = self._params[CLIENT_ID]
      client_params['client_secret'] = self._params[CLIENT_SECRET]
      client_params['refresh_token'] = self._params[REFRESH_TOKEN]

    return client.GoogleAdsClient.load_from_dict(client_params)
