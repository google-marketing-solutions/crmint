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

"""CRMint's worker that push data into a Data Import on Google Analytics."""

import os
import tempfile

from google.cloud import storage

from jobs.workers import worker
from jobs.workers.ga import ga_utils
from jobs.workers.storage import storage_utils


class GADataImporter(worker.Worker):
  """Uploads CSV data from Cloud Storage to a Google Analytics Data Import."""

  PARAMS = [
      ('csv_uri', 'string', True, '',
       'CSV data file URI (e.g. gs://bucket/data.csv)'),
      ('account_id', 'string', True, '',
       'GA Account ID (e.g. 12345)'),
      ('property_id', 'string', True, '',
       'GA Property Tracking ID (e.g. UA-12345-3)'),
      ('dataset_id', 'string', True, '',
       'GA Dataset ID (e.g. sLj2CuBTDFy6CedBJw)'),
      ('max_uploads', 'number', False, None,
       'Maximum uploads to keep in GA Dataset (leave empty to keep all)'),
  ]

  def _log_upload_progress(self, progress: float):
    self.log_info(f'Uploaded {progress:.0%}')

  def _execute(self) -> None:
    client = ga_utils.get_client('analytics', 'v3')
    dataimport_ref = ga_utils.DataImportReference(
        account_id=self._params['account_id'],
        property_id=self._params['property_id'],
        dataset_id=self._params['dataset_id'])
    if self._params['max_uploads'] == 1:
      deleted_ids = ga_utils.delete_oldest_uploads(
          client, dataimport_ref, max_to_keep=None)
      self.log_info(f'Deleted all existing uploads for ids: {deleted_ids}')
    elif self._params['max_uploads']:
      deleted_ids = ga_utils.delete_oldest_uploads(
          client, dataimport_ref, max_to_keep=self._params['max_uploads'] - 1)
      self.log_info(f'Deleted oldest upload(s) for ids: {deleted_ids}')
    else:
      self.log_info('Kept all uploads')
    with tempfile.NamedTemporaryFile(delete=False) as temp:
      temp_filepath = temp.name
    storage_utils.download_file(storage.Client(),
                                uri_path=self._params['csv_uri'],
                                destination_path=temp_filepath)
    self.log_info('Downloaded file from Cloud Storage to App Engine')
    ga_utils.upload_dataimport(client,
                               dataimport_ref,
                               temp_filepath,
                               progress_callback=self._log_upload_progress)
    self.log_info('Successfully uploaded data import to Google Analytics')
    # Deletes the temporary file since it could be large (e.g. 1GB is common).
    os.remove(temp_filepath)
    self.log_info('Cleaned up the downloaded file')
