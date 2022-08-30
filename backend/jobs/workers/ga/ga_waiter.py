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

"""CRMint's worker that waits for various upload completions."""

from jobs.workers import worker
from jobs.workers.ga import ga_utils


class GADataImportUploadWaiter(worker.Worker):
  """Worker polling the upload status and respawning itself if not completed."""

  PARAMS = [
      ('account_id', 'string', True, '',
       'GA Account ID (e.g. 123456)'),
      ('property_id', 'string', True, '',
       'GA Property Tracking ID (e.g. UA-12345-3)'),
      ('dataset_id', 'string', True, '',
       'GA Dataset ID (e.g. sLj2CuBTDFy6CedBJw)'),
  ]

  def _execute(self) -> None:
    """Executes worker's logic.

    Raises:
      ValueError: Raised when the upload status is unsupported.
    """
    client = ga_utils.get_client('analytics', 'v3')
    dataimport_ref = ga_utils.DataImportReference(
        account_id=self._params['account_id'],
        property_id=self._params['property_id'],
        dataset_id=self._params['dataset_id'])
    status = ga_utils.get_dataimport_upload_status(client, dataimport_ref)
    if status == ga_utils.UploadStatus.PENDING:
      self._enqueue('GADataImportUploadWaiter', self._params.copy(), 60)
    elif status == ga_utils.UploadStatus.COMPLETED:
      self.log_info('Finished successfully')
    else:
      raise ValueError(f'Unknown Data Import upload status: {status}')
