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

from google.api_core import exceptions
from google.cloud.bigquery.job import ExtractJobConfig
from jobs.workers.bigquery.bq_worker import BQWorker


class BQToStorageExporter(BQWorker):  # pylint: disable=too-few-public-methods
  """Worker to export a BigQuery table to a CSV or JSON file."""

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('bq_dataset_location', 'string', True, '', 'BQ Dataset Location'),
      ('destination_uri', 'string', True, '',
       'Destination CSV or JSON file URI (e.g. gs://bucket/data.csv)'),
      ('print_header', 'boolean', True, False, 'Include a header row'),
      ('export_json', 'boolean', False, False, 'Export in JSON format'),
      ('export_gzip', 'boolean', False, False, 'Export GZIP-compressed'),
  ]

  def _execute_extract_table(
    self, destination_uri, bq_dataset_location, export_gzip,
    export_json, print_header):
    """Starts an data export job and waits fot it's completion."""
    client = self._get_client()
    job_id = self._get_job_id()
    if export_json:
      destination_format = 'NEWLINE_DELIMITED_JSON'
    else:
      destination_format = 'CSV'
    job_config = ExtractJobConfig(
        print_header=print_header,
        destination_format=destination_format,
        compression='GZIP' if export_gzip else 'NONE')
    try:
      job = client.get_job(job_id)
      job.reload()
    except exceptions.NotFound:
      job = client.extract_table(
        self._get_full_table_name(),
        destination_uri,
        job_id=job_id,
        job_config=job_config,
        location=bq_dataset_location)
    self._wait(job)
    
  def _execute(self):
    self._execute_extract_table(
      self._params['destination_uri'], self._params['bq_dataset_location'],
      self._params['export_gzip'], self._params['export_json'],
      self._params['print_header'])
