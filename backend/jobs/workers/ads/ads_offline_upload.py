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
from typing import List

from google.ads.googleads import client
from google.api_core import page_iterator

from jobs.workers.bigquery import bq_batch_worker, bq_worker


CONVERSION_UPLOAD_JSON_TEMPLATE = 'template'
CONVERSIONS_CUSTOMER_ID = 'customer_id'
DEVELOPER_TOKEN = 'google_ads_developer_token'
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
    (bq_worker.BQ_PROJECT_ID_PARAM_NAME,
     'string',
     True,
     '',
     'GCP Project ID where the BQ conversions table lives.'),
    (bq_worker.BQ_DATASET_NAME_PARAM_NAME,
     'string',
     True,
     '',
     'Dataset name where the BQ conversions table lives.'),
    (bq_worker.BQ_TABLE_NAME_PARAM_NAME,
     'string',
     True,
     '',
     'Table name where the BQ conversion data lives.'),
    (CONVERSION_UPLOAD_JSON_TEMPLATE,
     'string',
     True,
     '',
     'JSON template of a conversion upload request.'),
    (CONVERSIONS_CUSTOMER_ID,
     'string',
     True,
     '',
     'Customer ID of the account the conversions will be uploaded for.'),
  ]

  GLOBAL_SETTINGS = [
    DEVELOPER_TOKEN,
    SERVICE_ACCOUNT_FILE,
    REFRESH_TOKEN,
    CLIENT_ID,
    CLIENT_SECRET,
  ]

  def _validate_params(self) -> None:
    err_messages = []

    err_messages += self._validate_bq_params()
    err_messages += self._validate_ads_client_params()

    if err_messages:
      raise ValueError('The following param validation errors occurred:\n' +
                       '\n'.join(err_messages))

  def _validate_bq_params(self) -> List[str]:
    err_messages = []

    if not self._params.get(bq_worker.BQ_PROJECT_ID_PARAM_NAME, None):
      err_messages.append(
        '"'+bq_worker.BQ_PROJECT_ID_PARAM_NAME+'" is required.')

    if not self._params.get(bq_worker.BQ_DATASET_NAME_PARAM_NAME, None):
      err_messages.append(
        '"'+bq_worker.BQ_DATASET_NAME_PARAM_NAME+'" is required.')

    if not self._params.get(bq_worker.BQ_TABLE_NAME_PARAM_NAME, None):
      err_messages.append(
        '"'+bq_worker.BQ_TABLE_NAME_PARAM_NAME+'" is required.')

    return err_messages

  def _validate_ads_client_params(self) -> List[str]:
    err_messages = []
    is_service_account = SERVICE_ACCOUNT_FILE in self._params

    if not self._params.get(SERVICE_ACCOUNT_FILE, None) and not self._params.get(REFRESH_TOKEN, None):
      err_messages.append(
        'Either "'+SERVICE_ACCOUNT_FILE+'" or "'+REFRESH_TOKEN+'" are required')

    if not self._params.get(CONVERSION_UPLOAD_JSON_TEMPLATE, None):
      err_messages.append('"'+CONVERSION_UPLOAD_JSON_TEMPLATE+'" is required.')

    if not self._params.get(CONVERSIONS_CUSTOMER_ID, None):
      err_messages.append('"'+CONVERSIONS_CUSTOMER_ID+'" is required.')

    if not self._params.get(DEVELOPER_TOKEN, None):
      err_messages.append('"'+DEVELOPER_TOKEN+'" is required.')

    if not is_service_account and not self._params.get(CLIENT_ID, None) :
      err_messages.append('"'+CLIENT_ID+'" is required.')

    if not is_service_account and not self._params.get(CLIENT_SECRET, None):
      err_messages.append('"'+CLIENT_SECRET+'" is required.')

    return err_messages

  def _execute(self) -> None:
    """Begin the processing and upload of offline click conversions."""
    self._validate_params()
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
