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

"""CRMint's abstract worker dealing with Vertex AI."""

import time

import google.auth

from google.cloud import aiplatform

from google.cloud.aiplatform_v1.types import job_state as js
from google.cloud.aiplatform_v1.types import pipeline_state as ps

from jobs.workers import worker


_PIPELINE_COMPLETE_STATES = frozenset([
    ps.PipelineState.PIPELINE_STATE_SUCCEEDED,
    ps.PipelineState.PIPELINE_STATE_FAILED,
    ps.PipelineState.PIPELINE_STATE_CANCELLED,
    ps.PipelineState.PIPELINE_STATE_PAUSED])

_JOB_COMPLETE_STATES = frozenset([
    js.JobState.JOB_STATE_SUCCEEDED,
    js.JobState.JOB_STATE_FAILED,
    js.JobState.JOB_STATE_CANCELLED,
    js.JobState.JOB_STATE_PAUSED])


class VertexAIWorker(worker.Worker):
  """Worker that polls job status and respawns itself if the job is not done."""

  def _get_vertexai_job_client(self, location):
    api_endpoint = f'{location}-aiplatform.googleapis.com'
    client_options = {'api_endpoint': api_endpoint}
    return aiplatform.gapic.JobServiceClient(client_options=client_options)

  def _get_vertexai_pipeline_client(self, location):
    api_endpoint = f'{location}-aiplatform.googleapis.com'
    client_options = {'api_endpoint': api_endpoint}
    return aiplatform.gapic.PipelineServiceClient(client_options=client_options)

  def _get_vertexai_dataset_client(self, location):
    api_endpoint = f'{location}-aiplatform.googleapis.com'
    client_options = {'api_endpoint': api_endpoint}
    return aiplatform.gapic.DatasetServiceClient(client_options=client_options)

  def _get_vertexai_model_client(self, location):
    api_endpoint = f'{location}-aiplatform.googleapis.com'
    client_options = {'api_endpoint': api_endpoint}
    return aiplatform.gapic.ModelServiceClient(client_options=client_options)

  def _get_batch_prediction_job(self, job_client, job_name):
    return job_client.get_batch_prediction_job(name=job_name)

  def _get_training_pipeline(self, pipeline_client, pipeline_name):
    return pipeline_client.get_training_pipeline(name=pipeline_name)

  def _get_location_from_pipeline_name(self, pipeline_name):
    return pipeline_name.split('/')[3]

  def _get_location_from_job_name(self, job_name):
    return job_name.split('/')[3]

  def _get_project_id(self):
    _, project_id = google.auth.default()
    return project_id

  def _get_parent_resource(self, location):
    project_id = self._get_project_id()
    return f'projects/{project_id}/locations/{location}'

  def _wait_for_pipeline(self, pipeline):
    """Waits for pipeline completion.

    It will relay to VertexAIWaiter if it takes too long.
    """
    delay = 5
    waiting_time = 5
    time.sleep(delay)
    while pipeline.state not in _PIPELINE_COMPLETE_STATES:
      if waiting_time > 300:  # Once 5 minute has passed, spawn VertexAIWaiter.
        self._enqueue(
            'VertexAIWaiter', {
                'id': pipeline.name,
                'worker_class': 'VertexAITabularTrainer'
            }, 60)
        return None
      if delay < 30:
        delay = [5, 10, 15, 20, 30][int(waiting_time / 60)]
      time.sleep(delay)
      waiting_time += delay
    if pipeline.state == ps.PipelineState.PIPELINE_STATE_FAILED:
      raise worker.WorkerException(f'Training pipeline {pipeline.name} failed.')

  def _wait_for_job(self, job):
    """Waits for batch prediction job completion.

    It will relay to VertexAIWaiter if it takes too long.
    """
    delay = 5
    waiting_time = 5
    time.sleep(delay)
    while job.state not in _JOB_COMPLETE_STATES:
      if waiting_time > 300:  # Once 5 minute has passed, spawn VertexAIWaiter.
        self._enqueue(
            'VertexAIWaiter', {
                'id': job.name,
                'worker_class': 'VertexAIBatchPredictorToBQ'},
            60)
        return None
      if delay < 30:
        delay = [5, 10, 15, 20, 30][int(waiting_time / 60)]
      time.sleep(delay)
      waiting_time += delay
    if job.state == js.JobState.JOB_STATE_FAILED:
      raise worker.WorkerException(f'Job {job.name} failed.')

  def _clean_up_datasets(self, dataset_client, project, region, display_name):
    parent = f'projects/{project}/locations/{region}'
    datasets = list(
        dataset_client.list_datasets({
            'parent': parent,
            'filter': f'display_name="{display_name}"',
            'order_by': 'create_time asc'}))
    configs = map(lambda x: (x.create_time, {'name': x.name}), datasets)
    sorted_configs = sorted(configs)
    for _, config in sorted_configs[:-1]:
      dataset_name = config['name']
      dataset_client.delete_dataset({'name': dataset_name})
      self.log_info(f'Deleted dataset: {dataset_name}')

  def _clean_up_training_pipelines(self, pipeline_client, project, region,
                                   display_name):
    parent = f'projects/{project}/locations/{region}'
    training_pipelines = list(
        pipeline_client.list_training_pipelines({
            'parent': parent,
            'filter': f'display_name="{display_name}"'}))
    configs = map(
        lambda x: (x.create_time, {'state': x.state, 'name': x.name}),
        training_pipelines)
    sorted_configs = sorted(configs)
    for _, config in sorted_configs[:-1]:
      training_pipeline_name = config['name']
      if config['state'] in _PIPELINE_COMPLETE_STATES:
        pipeline_client.delete_training_pipeline(name=training_pipeline_name)
      else:
        pipeline_client.cancel_training_pipeline(
            name=training_pipeline_name, timeout=300)
        pipeline_client.delete_training_pipeline(name=training_pipeline_name)
      self.log_info(f'Deleted training pipeline: {training_pipeline_name}')

  def _clean_up_batch_predictions(self, job_client, project, region,
                                  display_name):
    parent = f'projects/{project}/locations/{region}'
    batch_predictions = list(
        job_client.list_batch_prediction_jobs({
            'parent': parent,
            'filter': f'display_name="{display_name}"'}))
    configs = map(
        lambda x: (x.create_time, {'state': x.state, 'name': x.name}),
        batch_predictions)
    sorted_configs = sorted(configs)
    for _, config in sorted_configs[:-1]:
      batch_prediction_name = config['name']
      if config['state'] in _JOB_COMPLETE_STATES:
        job_client.delete_batch_prediction_job(name=batch_prediction_name)
      else:
        job_client.cancel_batch_prediction_job(
            name=batch_prediction_name, timeout=300)
        job_client.delete_batch_prediction_job(name=batch_prediction_name)
      self.log_info(f'Deleted batch prediction: {batch_prediction_name}')
