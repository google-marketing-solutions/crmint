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

"""CRMint's workers to stream data from BigQuery to Google Analytics.

We stream data from BigQuery to the Measurement Protocol API, which doesn't
need credentials to authenticate calls, instead it uses a secret key to
control access.
"""

import json
import math
import string
import urllib

from google.api_core import page_iterator
import requests

from jobs.workers import worker
from jobs.workers.bigquery import bq_worker
from jobs.workers.ga import ga_utils


class BQToMeasurementProtocolGA4(bq_worker.BQWorker):
  """Reads a BigQuery table of arbitraty size and schedule processing tasks.

  This worker reads the table by chunks of `BQ_BATCH_SIZE` rows and feed these
  rows into a processing worker of type `BQToMeasurementProtocolProcessorGA4`.
  This ensures that we never timeout on large tables, especially since Pub/Sub
  might be very sensitive to long running tasks not returning a status quickly
  enough.

  If we enqueued more than `MAX_ENQUEUED_JOBS` processing tasks, we stop
  enqueuing new processing tasks and schedule a new `BQToMeasurementProtocolGA4`
  worker with the `bq_page_token` parameter pointing to the next page to read
  from. This also ensures that we never timeout on large tables.
  """

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('bq_dataset_location', 'string', True, '', 'BQ Dataset Location'),
      ('measurement_id', 'string', True, '', ('Measurement ID / '
                                              'Firebase App ID')),
      ('api_secret', 'string', True, '', 'API Secret'),
      ('template', 'text', True, '', ('GA4 Measurement Protocol '
                                      'JSON template')),
      ('mp_batch_size', 'number', True, 20, ('Measurement Protocol '
                                             'batch size')),
      ('debug', 'boolean', True, False, 'Debug mode'),
  ]

  # BigQuery batch size for querying results.
  BQ_BATCH_SIZE = 1000

  # Maximum number of jobs to enqueued before spawning a new scheduler.
  MAX_ENQUEUED_JOBS = 50

  def _execute(self) -> None:
    client = self._get_client()
    bq_project_id = self._params['bq_project_id']
    bq_dataset_id = self._params['bq_dataset_id']
    dataset = client.get_dataset(f'{bq_project_id}.{bq_dataset_id}')
    page_token = self._params.get('bq_page_token', None)
    row_iterator = client.list_rows(
        dataset.table(self._params['bq_table_id']),
        page_token=page_token,
        page_size=self.BQ_BATCH_SIZE)

    enqueued_jobs_count = 0
    for _ in row_iterator.pages:
      # Enqueue job for this page
      worker_params = self._params.copy()
      worker_params['bq_page_token'] = page_token
      worker_params['bq_batch_size'] = self.BQ_BATCH_SIZE
      self._enqueue('BQToMeasurementProtocolProcessorGA4', worker_params, 0)
      enqueued_jobs_count += 1

      # Updates the page token reference for the next iteration.
      page_token = row_iterator.next_page_token

      # Spawns a new job to schedule the remaining pages.
      if (enqueued_jobs_count >= self.MAX_ENQUEUED_JOBS
          and page_token is not None):
        worker_params = self._params.copy()
        worker_params['bq_page_token'] = page_token
        self._enqueue(self.__class__.__name__, worker_params, 0)
        return


class BQToMeasurementProtocolProcessorGA4(bq_worker.BQWorker):
  """Reads the provided table chunk and stream it to Measurement Protocol API.

  A chunk is fully determined by two parameters: `bq_page_token` and
  `bq_batch_size`. This worker will read this given chunk and stream its
  content to the Measurement Protocol API for GA4 Properties.
  """

  def _send_payload(self, payload, url_param) -> None:
    if self._params['debug']:
      domain = 'https://www.google-analytics.com/debug/mp/collect'
    else:
      domain = 'https://www.google-analytics.com/mp/collect'

    querystring = urllib.parse.urlencode({
        url_param: self._params['measurement_id'],
        'api_secret': self._params['api_secret'],
    })
    response = requests.post(f'{domain}?{querystring}',
                             data=json.dumps(payload),
                             headers={'content-type': 'application/json'})
    if self._params['debug']:
      for msg in response.json()['validationMessages']:
        self.log_warn(f'Validation Message: {msg["description"]}, '
                      f'Payload: {payload}')
    else:
      if response.status_code != requests.codes.no_content:
        raise worker.WorkerException(f'Failed to send event with status code '
                                     f'({response.status_code}) and '
                                     f'parameters: {payload}')

  def _stream_rows(self, page: page_iterator.Page, url_param: str) -> None:
    # Warns users if they are using an unsupported formatting syntax.
    if '%(' in self._params['template']:
      self.log_warn(
          'It seems you are using an unsupported formatting syntax, '
          'please update to the Template Strings syntax: '
          'https://docs.python.org/3/library/string.html#template-strings.')

    # TODO(dulacp): Migrate to jinja2 templates, will help for batches
    # TODO(dulacp): Implement batches to optimize the overall upload duration.
    num_rows = page.num_items
    template = string.Template(self._params['template'])
    for idx, row in enumerate(page):
      payload = template.substitute(dict(row.items()))
      self._send_payload(json.loads(payload), url_param)
      if idx % (math.ceil(num_rows / 10)) == 0:
        progress = idx / num_rows
        self.log_info(f'Completed {progress:.2%} of the measurement '
                      f'protocol hits')
    self.log_info('Done with measurement protocol hits.')

  def _execute(self) -> None:
    client = self._get_client()
    dataset = client.get_dataset(
        f'{self._params["bq_project_id"]}.{self._params["bq_dataset_id"]}')
    row_iterator = client.list_rows(
        dataset.table(self._params['bq_table_id']),
        page_token=self._params.get('bq_page_token', None),
        page_size=self._params['bq_batch_size'])
    url_param = ga_utils.get_url_param_by_id(self._params['measurement_id'])
    # We are only interested in the first page results, since our chunk is
    # fully specicifed by (page_token, batch_size). The next page will be
    # processed by another processing instance.
    first_page = next(row_iterator.pages)
    self._stream_rows(first_page, url_param)
