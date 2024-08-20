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

"""CRMint's worker that waits for a BigQuery job completion."""


from jobs.workers import worker
from jobs.workers.bigquery import bq_worker


class BQWaiter(bq_worker.BQWorker):
  """Worker that polls job status and respawns itself if the job is not done."""

  def _execute(self):
    client = self._get_client()
    job = client.get_job(
      job_id=self._params['job_id'],
      location=self._params['location'])
    if job.error_result:
      raise worker.WorkerException(job.error_result['message'])
    if not job.done():
      self.log_info(f'Current BigQuery job state: {job.state}')
      self._enqueue('BQWaiter', {'job_id': job.job_id, 'location': job.location}, 60)
    else:
      self.log_info('Finished successfully!')
