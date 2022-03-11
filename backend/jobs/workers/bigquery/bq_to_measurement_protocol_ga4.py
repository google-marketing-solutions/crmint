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
from jobs.workers.worker import Worker, WorkerException
from jobs.workers.bigquery.bq_worker import BQWorker

class BQToMeasurementProtocolGA4(BQWorker):
  """Worker to push data through Measurement Protocol."""

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('bq_dataset_location', 'string', True, '', 'BQ Dataset Location'),
      ('measurement_id', 'string', True, '', 'Measurement ID'),
      ('api_secret', 'string', True, '', 'API Secret'),
      ('template', 'text', True, '', ('GA4 Measurement Protocol '
                                      'JSON template')),
      ('mp_batch_size', 'number', True, 20, ('Measurement Protocol '
                                             'batch size')),
      ('debug', 'boolean', True, False, 'Debug mode'),
  ]

  # BigQuery batch size for querying results. Default to 1000.
  BQ_BATCH_SIZE = int(1e3)

  # Maximum number of jobs to enqueued before spawning a new scheduler.
  MAX_ENQUEUED_JOBS = 1000

  def _execute(self):
    project_id = self._params['bq_project_id']
    dataset_id = self._params['bq_dataset_id']
    self._client = self._get_client()
    self._dataset = self._client.get_dataset(f'{project_id}.{dataset_id}')
    self._table = self._dataset.table(self._params['bq_table_id'])
    page_token = self._params.get('bq_page_token', None)
    query_iterator = self._client.list_rows(
        self._table,
        page_token=page_token,
        page_size=1000)

    enqueued_jobs_count = 0
    for query_page in query_iterator.pages:  # pylint: disable=unused-variable
      # Enqueue job for this page
      worker_params = self._params.copy()
      worker_params['bq_page_token'] = page_token
      self._enqueue('BQToMeasurementProtocolProcessorGA4', worker_params, 0)
      enqueued_jobs_count += 1

      # Updates the page token reference for the next iteration.
      page_token = query_iterator.next_page_token

      # Spawns a new job to schedule the remaining pages.
      if (enqueued_jobs_count >= self.MAX_ENQUEUED_JOBS
          and page_token is not None):
        worker_params = self._params.copy()
        worker_params['bq_page_token'] = page_token
        self._enqueue(self.__class__.__name__, worker_params, 0)
        return
