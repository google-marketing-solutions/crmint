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

"""CRMint's worker executing Vertex AI tabular training."""

from google.cloud import aiplatform
from jobs.workers.vertexai import vertexai_worker


class VertexAITabularTrainer(vertexai_worker.VertexAIWorker):
  """Worker to train a Vertex AI AutoML model using a Vertex dataset."""

  PARAMS = [
      ('project_id', 'string', True, '', 'Project ID'),
      ('vertexai_region', 'string', True, '', 'Vertex AI Region'),
      ('vertexai_dataset_name', 'string', True, '', 'Vertex AI Dataset Name'),
      ('prediction_type', 'string', True, '', 'Prediction Type '
                                              '(regression or classification)'),
      ('target_column', 'string', True, '', 'Target Column'),
      ('budget_hours', 'number', True, 1, 'Training Budget Hours (1 thru 72)'),
      ('vertexai_model_name', 'string', True, '', 'Vertex AI Model Name'),
      ('clean_up', 'boolean', True, True, 'Clean Up'),
  ]

  def _get_vertexai_tabular_dataset(self, dataset_client, vertexai_region):
    display_name = self._params['vertexai_dataset_name']
    parent_resource = self._get_parent_resource(vertexai_region)
    dataset = dataset_client.list_datasets({
        'parent': parent_resource,
        'filter': f'display_name="{display_name}"'})
    if len(list(dataset)) > 1:
      dataset = dataset_client.list_datasets({
          'parent': parent_resource,
          'filter': f'display_name="{display_name}"',
          'order_by': 'create_time desc'})
    if dataset:
      first_dataset = list(dataset)[0]
      return aiplatform.TabularDataset(dataset_name=first_dataset.name)
    return None

  def _clean_up_models(self, model_client, vertexai_region,
                       vertexai_model_name):
    parent_resource = self._get_parent_resource(vertexai_region)
    try:
      models = model_client.list_models({
          'parent': parent_resource,
          'filter': f'display_name={vertexai_model_name}',
          'order_by': 'create_time asc'})
      if models:
        for model in list(models)[:-1]:
          model_client.delete_model({'name': model.name})
          self.log_info(f'Deleted model: {model.name}')
    except Exception as e:
      self.log_info(f'Exception: {e}')

  def _create_automl_tabular_training_job(
      self, vertexai_model_name, prediction_type):
    return aiplatform.AutoMLTabularTrainingJob(
        display_name=f'{vertexai_model_name}',
        optimization_prediction_type=f'{prediction_type}')

  def _execute(self):
    aiplatform.init(
        project=self._get_project_id(),
        location=self._params['vertexai_region'])
    project_id = self._params['project_id']
    budget_hours = self._params['budget_hours']
    target_column = self._params['target_column']
    vertexai_model_name = self._params['vertexai_model_name']
    vertexai_region = self._params['vertexai_region']
    prediction_type = self._params['prediction_type']
    vertexai_dataset_name = self._params['vertexai_dataset_name']
    dataset_client = self._get_vertexai_dataset_client(vertexai_region)
    pipeline_client = self._get_vertexai_pipeline_client(vertexai_region)
    model_client = self._get_vertexai_model_client(vertexai_region)
    dataset = self._get_vertexai_tabular_dataset(
        dataset_client, vertexai_region)
    if not dataset:
      raise ValueError(f'No Vertex AI dataset found with name '
                       f'{vertexai_dataset_name}. Try again.')
    if self._params['clean_up']:
      self._clean_up_training_pipelines(
          pipeline_client, project_id, vertexai_region, vertexai_model_name)
      self._clean_up_models(model_client, vertexai_region, vertexai_model_name)
    job = self._create_automl_tabular_training_job(
        vertexai_model_name, prediction_type)
    formatted_budget_hours = budget_hours * 1000
    job.run(
        dataset=dataset,
        target_column=f'{target_column}',
        budget_milli_node_hours=formatted_budget_hours,
        model_display_name=f'{vertexai_model_name}',
        is_default_version=True,
        disable_early_stopping=False,
        sync=False)
    job.wait_for_resource_creation()
    pipeline_name = job.resource_name
    pipeline = self._get_training_pipeline(pipeline_client, pipeline_name)
    self._wait_for_pipeline(pipeline)
