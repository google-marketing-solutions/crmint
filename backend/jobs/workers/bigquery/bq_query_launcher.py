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

"""Legacy workers running SQL queries.

These legacy workers will log a warning message inviting the CRMint end user to
update their jobs with the new `bq_script_executor.BQScriptExecutor` worker.
"""

from google.cloud import bigquery

from jobs.workers.bigquery import bq_script_executor


class BQQueryLauncher(bq_script_executor.BQScriptExecutor):
  """Worker to run a SQL query and store its results in a table.

  *Deprecated since CRMint 2.0:* Switch to the new `BQScriptExecutor` worker.
  """

  PARAMS = [
      ('query', 'sql', True, '', 'SQL query'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('bq_dataset_location', 'string', True, '', 'BQ Dataset Location'),
      ('overwrite', 'boolean', True, False, 'Overwrite table'),
  ]

  def _execute(self) -> None:
    self.log_warn('Deprepcated: BQQueryLauncher has been deprecated, please '
                  'upgrade to the new BQScriptExecutor worker.')
    if self._params['overwrite']:
      write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
    else:
      write_disposition = bigquery.WriteDisposition.WRITE_APPEND
    dataset_ref = bigquery.DatasetReference(
        self._params['bq_project_id'], self._params['bq_dataset_id'])
    table_ref = bigquery.TableReference(
        dataset_ref, self._params['bq_table_id'])
    job_config = bigquery.QueryJobConfig(
        destination=table_ref,
        write_disposition=write_disposition)
    client = self._get_client()
    job = client.query(
        self._params['query'].strip(),
        job_id_prefix=self._get_prefix(),
        location=self._params['bq_dataset_location'],
        job_config=job_config)
    self._wait(job)
