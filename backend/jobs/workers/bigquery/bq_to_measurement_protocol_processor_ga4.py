# Copyright 2021 Google Inc. All rights reserved.
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

import json
import requests
from jobs.workers.worker import Worker, WorkerException
from jobs.workers.bigquery.bq_worker import BQWorker

class BQToMeasurementProtocolProcessorGA4(BQWorker):
  """Worker pushing to Measurement Protocol for GA4 Properties."""

  def _send_payload_list(self, payloads):
    headers = {'content-type': 'application/json'}
    measurement_id = self._measurement_id
    api_secret = self._api_secret
    for payload in payloads:
      if self._debug:
        domain = 'https://www.google-analytics.com/debug/mp/collect'
        url = f'{domain}?measurement_id={measurement_id}&api_secret={api_secret}'
        response = requests.post(
          url,
          data=json.dumps(payload),
          headers=headers)
        result = json.loads(response.text)
        for msg in result['validationMessages']:
          self.log_warn('Validation Message: %s, Payload: %s' % (
            msg['description'], payload))
      else:
        domain = 'https://www.google-analytics.com/mp/collect'
        url = f'{domain}?measurement_id={measurement_id}&api_secret={api_secret}'
        response = requests.post(
          url,
          data=json.dumps(payload),
          headers=headers)
        if response.status_code != requests.codes.no_content:
          raise WorkerException(
            'Failed to send event with status code (%s) and parameters: %s'
            % (response.status_code, payload))

  def _calculate_hits_sent(self, iters, rows):
    """Calculates the proportion of measurement protocol hits completed."""
    if not rows:
      return 0
    hits_sent = float(self._params['mp_batch_size']) * float(iters)
    percent_complete = hits_sent / float(rows)
    return int(percent_complete * 100)

  def _process_query_results(self, query_data, query_schema, total_rows):
    """Sends event hits from query data."""
    fields = [f.name for f in query_schema]
    payload_list = []
    i = 0
    logs = []
    for row in query_data:
      template = self._params['template'] % dict(zip(fields, row))
      measurement_protocol_payload = json.loads(template)
      payload_list.append(measurement_protocol_payload)
      if len(payload_list) >= self._params['mp_batch_size']:
        self._send_payload_list(payload_list)
        payload_list = []
        i += 1
        completed = self._calculate_hits_sent(i, total_rows)
        if completed % 10 == 0 and completed not in logs:
          self.log_info(
            'Completed {}%% of the measurement protocol hits'.format(completed))
          logs.append(completed)
    if payload_list:
      # Sends remaining payloads.
      self._send_payload_list(payload_list)
      self.log_info(
        'Completed 100%% of the measurement protocol hits')

  def _execute(self):
    # BQ Setup
    project_id = self._params['bq_project_id']
    dataset_id = self._params['bq_dataset_id']
    self._client = self._get_client()
    self._dataset = self._client.get_dataset(f'{project_id}.{dataset_id}')
    self._table = self._dataset.table(self._params['bq_table_id'])
    self._debug = self._params['debug']
    self._measurement_id = self._params['measurement_id']
    self._api_secret = self._params['api_secret']
    page_token = self._params['bq_page_token'] or None
    query_iterator = self._client.list_rows(
        self._table,
        page_token=page_token,
        page_size=1000)
    query_first_page = next(query_iterator.pages)
    results = list(query_first_page)
    total_rows = len(list(query_first_page))
    self._process_query_results(
        results, query_iterator.schema, total_rows)
    self.log_info('Finished successfully')
