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

"""Legacy worker running SQL queries; please use BQScriptExecutor instead."""

from google.api_core import exceptions
from google.cloud.bigquery.job import QueryJobConfig
from jobs.workers.bigquery.bq_worker import BQWorker


class BQQueryLauncher(BQWorker):  # pylint: disable=too-few-public-methods
  """Legacy worker to run SQL queries and store results in tables."""

  PARAMS = [
      ('query', 'sql', True, '', 'SQL query'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('bq_dataset_location', 'string', True, '', 'BQ Dataset Location'),
      ('overwrite', 'boolean', True, False, 'Overwrite table'),
  ]

  def _execute(self):
    client = self._get_client()
    job_id = self._get_job_id()
    destination_table = self._get_full_table_name()
    query = self._params['query'].strip()
    location = self._params['bq_dataset_location']
    try:
      job = client.get_job(job_id)
      job.reload()
    except exceptions.NotFound:
      if self._params['overwrite']:
        write_disposition = 'WRITE_TRUNCATE'
      else:
        write_disposition = 'WRITE_APPEND'
      job_config = QueryJobConfig(
        destination=destination_table,
        write_disposition=write_disposition,
      )
      job = client.query(
        query=query, job_id=job_id, location=location, job_config=job_config)
    self._wait(job)
