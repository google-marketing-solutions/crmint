# Copyright 2023 Google Inc. All rights reserved.
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
import json
import math
import string

from typing import Any, List

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
LOG_UPLOAD_RESPONSE_DETAILS = 'log_upload_response_details'


class BQToAdsOfflineClickConversion(bq_batch_worker.BQBatchDataWorker):
  """Worker that reads conversions from a BQ table and uploading into Ads.

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
    (LOG_UPLOAD_RESPONSE_DETAILS,
     'bool',
     False,
     False,
     'Flag determining if each conversion upload response should be logged'),
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
    self.log_info('Validating parameters now.')
    self._validate_params()
    super()._execute()

  def _get_sub_worker_name(self) -> str:
    return AdsOfflineClickPageResultsWorker.__name__


class AdsOfflineClickPageResultsWorker(bq_batch_worker.TablePageResultsProcessorWorker):
  """A page results worker for uploading a chunk of conversion data."""

  def _process_page_results(self, page_data: page_iterator.Page) -> None:
    ads_client = self._get_ads_client()
    num_rows = page_data.num_items
    template = string.Template(self._params['template'])

    conversion_objs = []
    for idx, row in enumerate(page_data):
      payload = template.substitute(dict(row.items()))
      conversion_objs.append(
        self._generate_conversion_object(json.loads(payload), ads_client)
      )

      if idx % (math.ceil(num_rows / 10)) == 0:
        progress = idx / num_rows
        self.log_info(f'Completed {progress:.2%} of the google ads conversion uploads.')

    self._send_payload(conversion_objs, ads_client)
    self.log_info('Done with google ads conversion uploads.')

  def _get_ads_client(self) -> client.GoogleAdsClient:
    client_params = {'developer_token': self._params[DEVELOPER_TOKEN]}
    client_params['use_proto_plus'] = 'True'

    self.log_info('Setting up Ads client for user flow.')
    client_params['client_id'] = self._params[CLIENT_ID]
    client_params['client_secret'] = self._params[CLIENT_SECRET]
    client_params['refresh_token'] = self._params[REFRESH_TOKEN]

    return client.GoogleAdsClient.load_from_dict(client_params)

  def _generate_conversion_object(
    self,
    conversion_data: Any,
    ads_client: client.GoogleAdsClient
  ) -> Any:
    """Generates an Ads API conversion object."""
    click_conversion = ads_client.get_type("ClickConversion")

    click_conversion.gclid = conversion_data['gclid']
    click_conversion.conversion_value = conversion_data['conversionValue']
    click_conversion.conversion_date_time = conversion_data[
      'conversionDateTime']
    click_conversion.currency_code = conversion_data['currencyCode']
    click_conversion.conversion_action = conversion_data['conversionAction']

    return click_conversion

  def _send_payload(
    self, payload: List[Any], ads_client: client.GoogleAdsClient
  ) -> None:
    request = ads_client.get_type("UploadClickConversionsRequest")
    request.customer_id = self._params[CONVERSIONS_CUSTOMER_ID]
    request.conversions.extend(payload)
    request.partial_failure = True

    conversion_upload_service = ads_client.get_service(
      "ConversionUploadService"
    )
    conversion_upload_response = (
      conversion_upload_service.upload_click_conversions(request=request)
    )

    upload_status = conversion_upload_response.status
    self.log_info(
      f'[Conversion Upload] Response status code:  {upload_status.code}')
    self.log_info(
      f'[Conversion Upload] Response status message:  {upload_status.message}')

    if self._params.get(LOG_UPLOAD_RESPONSE_DETAILS, False):
      self._log_upload_response_error_details(conversion_upload_response)

  def _log_upload_response_error_details(self, upload_response: Any) -> None:
    error_details = upload_response.status.details
    for detail in error_details:
      self.log_info(f'Error detail:  {detail}')

