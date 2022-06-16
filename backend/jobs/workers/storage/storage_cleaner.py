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

"""CRMint's worker that deletes selected files from Cloud Storage."""

import datetime

from google.cloud import storage

from jobs.workers import worker
from jobs.workers.storage import storage_utils


class StorageCleaner(worker.Worker):
  """Worker to delete stale files in Cloud Storage."""

  PARAMS = [
      ('file_uris', 'string_list', True, '',
       ('List of file URIs and URI patterns (e.g. gs://bucket/data.csv or '
        'gs://bucket/data_*.csv)')),
      ('expiration_days', 'number', True, 30,
       'Days to keep files since last modification'),
  ]

  def _execute(self):
    max_delta = datetime.timedelta(days=self._params['expiration_days'])
    now_dt = datetime.datetime.now(tz=datetime.timezone.utc)
    client = storage.Client()
    blobs = storage_utils.get_matching_blobs(client, self._params['file_uris'])
    for blob in blobs:
      # NB: `blob.updated` contains the datetime of last updates.
      last_update_dt = blob.updated
      if not last_update_dt.tzinfo:
        last_update_dt = last_update_dt.replace(tzinfo=datetime.timezone.utc)
      if (now_dt - last_update_dt) > max_delta:
        blob.delete()
        self.log_info(f'Deleted file at gs://{blob.bucket.name}/{blob.name}')
