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

"""Worker to export a BigQuery table to a CSV or JSON file."""


from google.cloud import bigquery

from jobs.workers.bigquery import bq_worker


class BQToStorageExporter(bq_worker.BQWorker):
  """Worker to export a BigQuery table to a CSV or JSON file."""

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('destination_uri', 'string', True, '',
       'Destination CSV or JSON file URI (e.g. gs://bucket/data.csv)'),
      ('print_header', 'boolean', True, False, 'Include a header row'),
      ('export_json', 'boolean', False, False, 'Export in JSON format'),
      ('export_gzip', 'boolean', False, False, 'Export GZIP-compressed'),
  ]

  def _execute(self):
    """Starts an data export job and waits fot its completion."""
    if self._params['export_json']:
      destination_format = 'NEWLINE_DELIMITED_JSON'
    else:
      destination_format = 'CSV'
    job_config = bigquery.ExtractJobConfig(
        print_header=self._params['print_header'],
        destination_format=destination_format,
        compression='GZIP' if self._params['export_gzip'] else 'NONE')
    dataset_ref = bigquery.DatasetReference(
        self._params['bq_project_id'], self._params['bq_dataset_id'])
    client = self._get_client()
    job = client.extract_table(
        bigquery.TableReference(dataset_ref, self._params['bq_table_id']),
        destination_uris=self._params['destination_uri'],
        job_id_prefix=self._get_prefix(),
        job_config=job_config)
    self._wait(job)
