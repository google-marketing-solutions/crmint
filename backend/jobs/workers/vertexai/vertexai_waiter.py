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

from google.cloud.aiplatform_v1.types import job_state as js
from google.cloud.aiplatform_v1.types import pipeline_state as ps

from jobs.workers import worker
from jobs.workers.vertexai import vertexai_worker


class VertexAIWaiter(vertexai_worker.VertexAIWorker):
  """Worker that polls job status and respawns itself if the job is not done."""

  def _execute_tabular_trainer(self):
    pipeline_name = self._params['id']
    location = self._get_location_from_pipeline_name(pipeline_name)
    client = self._get_vertexai_pipeline_client(location)
    pipeline = self._get_training_pipeline(client, pipeline_name)
    if pipeline.state == ps.PipelineState.PIPELINE_STATE_FAILED:
      raise worker.WorkerException(f'Training pipeline {pipeline.name} failed.')
    elif pipeline.state != ps.PipelineState.PIPELINE_STATE_SUCCEEDED:
      self._enqueue('VertexAIWaiter', {
          'id': self._params['id'],
          'worker_class': 'VertexAITabularTrainer'
      }, 60)
    elif pipeline.state == ps.PipelineState.PIPELINE_STATE_SUCCEEDED:
      self.log_info('Finished successfully!')

  def _execute_batch_predictor(self):
    job_name = self._params['id']
    location = self._get_location_from_job_name(job_name)
    client = self._get_vertexai_job_client(location)
    job = self._get_batch_prediction_job(client, job_name)
    if job.state == js.JobState.JOB_STATE_FAILED:
      raise worker.WorkerException(f'Job {job.name} failed.')
    elif job.state != js.JobState.JOB_STATE_SUCCEEDED:
      self._enqueue('VertexAIWaiter', {
          'id': self._params['id'],
          'worker_class': 'VertexAIBatchPredictorToBQ'
      }, 60)
    elif job.state == js.JobState.JOB_STATE_SUCCEEDED:
      self.log_info('Finished successfully!')

  def _execute(self):
    if self._params['worker_class'] == 'VertexAIBatchPredictorToBQ':
      self._execute_batch_predictor()
    if self._params['worker_class'] == 'VertexAITabularTrainer':
      self._execute_tabular_trainer()
