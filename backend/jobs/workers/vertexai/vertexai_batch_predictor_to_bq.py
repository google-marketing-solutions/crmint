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

"""CRMint's worker executing Vertex AI batch predictions to BigQuery."""

from google.cloud import aiplatform
from jobs.workers.vertexai import vertexai_worker


class VertexAIBatchPredictorToBQ(vertexai_worker.VertexAIWorker):
  """Worker to train a Vertex AI AutoML model using a Vertex dataset."""

  PARAMS = [
      ('vertexai_model_name', 'string', True, '', 'Vertex AI Model Name'),
      ('vertexai_batch_prediction_name', 'string', False, '',
       'Vertex AI Batch Prediction Name'),
      ('vertexai_region', 'string', True, '', 'Vertex AI Region'),
      ('bq_project_id', 'string', True, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('clean_up', 'boolean', True, True, 'Clean Up'),
  ]

  def _get_model(self, model_client, vertexai_region, vertexai_model_name):
    parent_resource = self._get_parent_resource(vertexai_region)
    models = model_client.list_models({
        'parent': parent_resource,
        'filter': f'display_name="{vertexai_model_name}"',
        'order_by': 'create_time desc'})
    for m in models:
      return aiplatform.Model(model_name=m.name)
    return None

  def _execute(self):
    aiplatform.init(
        project=self._get_project_id(),
        location=self._params['vertexai_region'])
    project_id = self._params['bq_project_id']
    dataset_id = self._params['bq_dataset_id']
    table_id = self._params['bq_table_id']
    vertexai_region = self._params['vertexai_region']
    model_client = self._get_vertexai_model_client(vertexai_region)
    model = self._get_model(model_client, vertexai_region,
                            self._params['vertexai_model_name'])
    if model is None:
      self.log_info('No model found. Please try again.')
      return
    job_client = self._get_vertexai_job_client(vertexai_region)
    batch_prediction_name = self._params['vertexai_batch_prediction_name']
    if batch_prediction_name is None:
      batch_prediction_name = f'{project_id}.{dataset_id}.{table_id}'
    if self._params['clean_up']:
      self._clean_up_batch_predictions(job_client, project_id, vertexai_region,
                                       batch_prediction_name)
    job = model.batch_predict(
        job_display_name=f'{batch_prediction_name}',
        instances_format='bigquery',
        predictions_format='bigquery',
        bigquery_source=f'bq://{project_id}.{dataset_id}.{table_id}',
        bigquery_destination_prefix=f'bq://{project_id}:{dataset_id}',
        sync=False)
    job.wait_for_resource_creation()
    batch_prediction_name = job.resource_name
    batch_prediction_job = self._get_batch_prediction_job(
        job_client, batch_prediction_name)
    self._wait_for_job(batch_prediction_job)
