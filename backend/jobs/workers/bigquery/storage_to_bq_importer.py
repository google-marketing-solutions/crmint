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


import json
from google.cloud import bigquery
from google.cloud.bigquery.job import LoadJobConfig
from jobs.workers.storage.storage_worker import StorageWorker
from jobs.workers.bigquery.bq_worker import BQWorker


class StorageToBQImporter(StorageWorker, BQWorker):  # pylint: disable=too-few-public-methods
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

  def _get_source_uris(self):
    blobs = self._get_matching_blobs(self._params['source_uris'])
    return [f'gs://{b.bucket.name}/{b.name}' for b in blobs]

  def _get_field_schema(self, field):
    name = field['name']
    field_type = field.get('type', 'STRING')
    mode = field.get('mode', 'NULLABLE')
    fields = field.get('fields', [])
    if fields:
      subschema = []
      for f in fields:
        fields_res = self._get_field_schema(f)
        subschema.append(fields_res)
    else:
      subschema = []
    field_schema = bigquery.schema.SchemaField(
      name=name,
      field_type=field_type,
      mode=mode,
      fields=tuple(subschema)
    )
    return field_schema

  def _parse_bq_json_schema(self, schema_json_string):
    table_schema = []
    jsonschema = json.loads(schema_json_string)
    for field in jsonschema:
      table_schema.append(self._get_field_schema(field))
    return table_schema

  def _execute(self):
    client = self._get_client()
    source_uris = self._get_source_uris()

    job_config = LoadJobConfig()
    if self._params['import_json']:
      job_config.source_format = 'NEWLINE_DELIMITED_JSON'
    else:
      try:
        job_config.skip_leading_rows = self._params['rows_to_skip']
      except KeyError:
        job_config.skip_leading_rows = 0
    job_config.autodetect = self._params['autodetect']
    if not job_config.autodetect:
      job_config.allow_jagged_rows = True
      job_config.allow_quoted_newlines = True
      job_config.ignore_unknown_values = True
      if self._params['schema']:
        job_config.schema = self._parse_bq_json_schema(self._params['schema'])
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

    job = client.load_table_from_uri(
        source_uris,
        self._get_full_table_name(),
        job_id_prefix=self._get_prefix(),
        job_config=job_config)
    self.log_info('Finished successfully')
    self._wait(job)
