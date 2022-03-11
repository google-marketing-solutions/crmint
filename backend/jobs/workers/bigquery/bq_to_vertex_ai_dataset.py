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

from google.cloud import aiplatform
#from jobs.workers.worker import Worker, WorkerException
from jobs.workers.vertexai.vertex_ai_worker import VertexAIWorker

class BQToVertexAIDataset(VertexAIWorker):
  """Worker to export a BigQuery table to a Vertex AI dataset."""

  PARAMS = [
      ('bq_project_id', 'string', True, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('bq_dataset_location', 'string', True, '', 'BQ Dataset Location'),
      ('vertex_ai_dataset_name', 'string', False, '', 'Vertex AI Dataset Name'),
      ('clean_up', 'boolean', True, True, 'Clean Up'),
  ]

  aiplatform.init()

  def _execute(self):
    project_id = self._params['bq_project_id']
    dataset_id = self._params['bq_dataset_id']
    table_id = self._params['bq_table_id']
    if not self._params['vertex_ai_dataset_name']:
      display_name = f'{project_id}.{dataset_id}.{table_id}'
    else:
      display_name = self._params['vertex_ai_dataset_name']
    if self._params['clean_up']:
      try:
        datasets = aiplatform.TabularDataset.list(
          filter=f"display_name={display_name}",
          order_by="create_time")
        if datasets:
          for i, dataset in enumerate(datasets[:-1]):
            d = datasets[i]
            aiplatform.TabularDataset.delete(d)
            self.log_info(f'Deleted dataset: {d.resource_name}.')
      except Exception as e:
        self.log_info(f'Exception: {e}')
    dataset = aiplatform.TabularDataset.create(
      display_name=display_name,
      bq_source=f'bq://{project_id}.{dataset_id}.{table_id}')
    dataset.wait()
    self.log_info(f'Dataset created: {dataset.resource_name}')
    self.log_info('Finished successfully')
