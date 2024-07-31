# Copyright 2024 Google Inc. All rights reserved.
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

"""CRMint's abstract worker dealing with BigQuery."""

import os
import time

from google.api_core.client_info import ClientInfo
from google.cloud import bigquery
from jobs.workers import worker


# Param name used to specify a BQ project ID
BQ_PROJECT_ID_PARAM_NAME = 'bq_project_id'

# Param name used to specify a BQ data set name
BQ_DATASET_NAME_PARAM_NAME = 'bq_dataset_id'

# Param name used to specify a BQ table name
BQ_TABLE_NAME_PARAM_NAME = 'bq_table_id'


class BQWorker(worker.Worker):
  """Abstract BigQuery worker."""

  _SCOPES = [
      'https://www.googleapis.com/auth/bigquery',
      'https://www.googleapis.com/auth/cloud-platform',
      'https://www.googleapis.com/auth/drive',
  ]

  def _get_client(self):
    client_info = None
    if 'REPORT_USAGE_ID' in os.environ:
      client_id = os.getenv('REPORT_USAGE_ID')
      opt_out = not bool(client_id)
      if not opt_out:
        client_info = ClientInfo(user_agent='cloud-solutions/crmint-usage-v3')
    return bigquery.Client(
      client_options={'scopes': self._SCOPES},
      client_info=client_info,
    )

  def _get_prefix(self):
    return f'{self._pipeline_id}_{self._job_id}_{self.__class__.__name__}'

  def _get_dry_run_job_config(self):
    return bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)

  def _generate_qualified_bq_table_name(self):
    return '.'.join([
      self._params.get(BQ_PROJECT_ID_PARAM_NAME, None),
      self._params.get(BQ_DATASET_NAME_PARAM_NAME, None),
      self._params.get(BQ_TABLE_NAME_PARAM_NAME, None),
    ])

  def _wait(self, job):
    """Waits for job completion and relays to BQWaiter if it takes too long."""
    time.sleep(5)
    if job.error_result:
      raise worker.WorkerException(job.error_result['message'])
    if not job.done():
      self._enqueue('BQWaiter', {'job_id': job.job_id}, 30)
