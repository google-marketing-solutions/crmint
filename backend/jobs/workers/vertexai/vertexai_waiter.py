# Copyright 2022 Google Inc. All rights reserved.
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

"""CRMint's worker that waits for a Vertex AI job completion."""

# copybara:strip_begin(internal google3 path)
from google.cloud.aiplatform import aiplatform
from google.cloud.aiplatform import aiplatform_v1 as aip_v1
# copybara:strip_end_and_replace_begin
# from google.cloud import aiplatform
# from google.cloud import aiplatform_v1 as aip_v1
# copybara:replace_end
from google.cloud.aiplatform.aiplatform_v1.types import job_state as js
from google.cloud.aiplatform.aiplatform_v1.types import pipeline_state as ps

from google3.third_party.professional_services.solutions.crmint.backend.jobs.workers.vertexai.vertexai_worker import VertexAIWorker
from google3.third_party.professional_services.solutions.crmint.backend.jobs.workers.worker import WorkerException


class VertexAIWaiter(VertexAIWorker):
  """Worker that polls job status and respawns itself if the job is not done."""

  def _execute_tabular_trainer(self):
    pipeline_name = self._params['id']
    location = self._get_location_from_pipeline_name(pipeline_name)
    client = self._get_vertexai_pipeline_client(location)
    pipeline = self._get_training_pipeline(client, pipeline_name)
    if pipeline.state == ps.PipelineState.PIPELINE_STATE_FAILED:
      raise WorkerException(f'Training pipeline {pipeline.name} failed.')
    if pipeline.state != ps.PipelineState.PIPELINE_STATE_SUCCEEDED:
      self._enqueue('VertexAIWaiter', {
          'id': self._params['id'],
          'worker_class': 'VertexAITabularTrainer'
      }, 60)
    if pipeline.state == ps.PipelineState.PIPELINE_STATE_SUCCEEDED:
      self.log_info('Finished successfully!')

  def _execute_batch_predictor(self):
    job_name = self._params['id']
    location = self._get_location_from_job_name(job_name)
    client = self._get_vertexai_job_client(location)
    job = self._get_batch_prediction_job(client, job_name)
    if job.state == js.JobState.JOB_STATE_FAILED:
      raise WorkerException(f'Job {job.name} failed.')
    if job.state != js.JobState.JOB_STATE_SUCCEEDED:
      self._enqueue('VertexAIWaiter', {
          'id': self._params['id'],
          'worker_class': 'VertexAIBatchPredictorToBQ'
      }, 60)
    if job.state == js.JobState.JOB_STATE_SUCCEEDED:
      self.log_info('Finished successfully!')

  def _execute(self):
    if self._params['worker_class'] == 'VertexAIBatchPredictorToBQ':
      self._execute_batch_predictor()
    if self._params['worker_class'] == 'VertexAITabularTrainer':
      self._execute_tabular_trainer()
