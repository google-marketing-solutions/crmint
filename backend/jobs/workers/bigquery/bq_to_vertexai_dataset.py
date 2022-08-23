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

from google.cloud import aiplatform
from jobs.workers.vertexai import vertexai_worker


class BQToVertexAIDataset(vertexai_worker.VertexAIWorker):
  """Worker to export a BigQuery table to a Vertex AI dataset."""

  PARAMS = [
      ('bq_project_id', 'string', True, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('bq_dataset_location', 'string', True, '', 'BQ Dataset Location'),
      ('vertexai_region', 'string', True, '', 'Vertex AI Region'),
      ('vertexai_dataset_name', 'string', False, '', 'Vertex AI Dataset Name'),
      ('clean_up', 'boolean', True, True, 'Clean Up'),
  ]

  def _get_tabular_dataset_client(self):
    return aiplatform.TabularDataset

  def _execute(self):
    aiplatform.init(
        project=self._get_project_id(),
        location=self._params['vertexai_region'])
    project_id = self._params['bq_project_id']
    dataset_id = self._params['bq_dataset_id']
    table_id = self._params['bq_table_id']
    vertexai_region = self._params['vertexai_region']
    vertexai_dataset_name = self._params['vertexai_dataset_name']
    dataset_client = self._get_vertexai_dataset_client(vertexai_region)
    if not vertexai_dataset_name:
      display_name = f'{project_id}.{dataset_id}.{table_id}'
    else:
      display_name = vertexai_dataset_name
    if self._params['clean_up']:
      self._clean_up_datasets(
          dataset_client, project_id, vertexai_region, display_name)
    tabular_dataset_client = self._get_tabular_dataset_client()
    tabular_dataset = tabular_dataset_client.create(
        display_name=display_name,
        bq_source=f'bq://{project_id}.{dataset_id}.{table_id}')
    tabular_dataset.wait()
    self.log_info(f'Dataset created: {tabular_dataset.resource_name}')
    self.log_info('Finished successfully')
