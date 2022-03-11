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

"""CRMint's abstract worker dealing with BigQuery."""


import time
import uuid
from google.cloud import bigquery
from jobs.workers.worker import Worker, WorkerException


class BQWorker(Worker):
  """Abstract BigQuery worker."""

  _SCOPES = [
      'https://www.googleapis.com/auth/bigquery',
      'https://www.googleapis.com/auth/cloud-platform',
      'https://www.googleapis.com/auth/drive',
  ]

  def _get_client(self):
    return bigquery.Client(client_options={'scopes': self._SCOPES})

  def _get_job_id(self):
    unique_id = str(uuid.uuid4()).replace('-', '_')
    return f'{self._pipeline_id}_{self._job_id}_{self.__class__.__name__}_{unique_id}'

  def _wait(self, job):
    """Waits for job completion and relays to BQWaiter if it takes too long."""
    delay = 5
    time.sleep(delay)
    job.reload()
    while job.state != 'DONE':
      self._enqueue('BQWaiter', {'bq_job_id': job.job_id}, 60)
      return
    if job.error_result is not None:
      raise WorkerException(job.error_result['message'])
    if job.state == 'DONE':
      self.log_info('Finished successfully.')

  def _get_full_table_name(self):
    project = self._params['bq_project_id'].strip()
    if project:
      project += '.'
    dataset = self._params['bq_dataset_id'].strip()
    table = self._params['bq_table_id'].strip()
    return f'{project}{dataset}.{table}'
