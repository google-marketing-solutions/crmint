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

"""Worker to import a CSV file into a BigQuery table."""

from google.cloud import bigquery
from google.cloud import storage

from jobs.workers.bigquery import bq_utils
from jobs.workers.bigquery import bq_worker
from jobs.workers.storage import storage_utils


class StorageToBQImporter(bq_worker.BQWorker):
  """Worker to import a CSV file into a BigQuery table."""

  PARAMS = [
      ('source_uris', 'string_list', True, '',
       'Source CSV or JSON files URIs (e.g. gs://bucket/data.csv)'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('overwrite', 'boolean', True, False, 'Overwrite table'),
      ('dont_create', 'boolean', True, False,
       'Don\'t create table if doesn\'t exist'),
      ('autodetect', 'boolean', True, False,
       'Autodetect schema and other parameters'),
      ('rows_to_skip', 'number', False, 0, 'Header rows to skip'),
      ('errors_to_allow', 'number', False, 0, 'Number of errors allowed'),
      ('import_json', 'boolean', False, False, 'Source is in JSON format'),
      ('csv_null_marker', 'string', False, '', 'CSV Null marker'),
      ('schema', 'text', False, '', 'Table Schema in JSON'),
  ]

  def _execute(self):
    job_config = bigquery.LoadJobConfig()

    if self._params['import_json']:
      job_config.source_format = 'NEWLINE_DELIMITED_JSON'
    else:
      job_config.skip_leading_rows = int(self._params['rows_to_skip'])
    job_config.autodetect = self._params['autodetect']

    if not job_config.autodetect:
      job_config.allow_jagged_rows = True
      job_config.allow_quoted_newlines = True
      job_config.ignore_unknown_values = True
      if self._params['schema']:
        job_config.schema = bq_utils.parse_bigquery_json_schema(
            self._params['schema'])

    if self._params['csv_null_marker']:
      job_config.null_marker = self._params['csv_null_marker']

    try:
      job_config.max_bad_records = self._params['errors_to_allow']
    except KeyError:
      job_config.max_bad_records = 0

    if self._params['overwrite']:
      job_config.write_disposition = 'WRITE_TRUNCATE'
    else:
      job_config.write_disposition = 'WRITE_APPEND'

    if self._params['dont_create']:
      job_config.create_disposition = 'CREATE_NEVER'
    else:
      job_config.create_disposition = 'CREATE_IF_NEEDED'

    gcs_client = storage.Client()
    matched_uris = storage_utils.get_matched_uris(gcs_client,
                                                  self._params['source_uris'])
    dataset_ref = bigquery.DatasetReference(
        self._params['bq_project_id'], self._params['bq_dataset_id'])
    bq_client = self._get_client()
    job = bq_client.load_table_from_uri(
        matched_uris,
        bigquery.TableReference(dataset_ref, self._params['bq_table_id']),
        job_id_prefix=self._get_prefix(),
        job_config=job_config)
    self._wait(job)
