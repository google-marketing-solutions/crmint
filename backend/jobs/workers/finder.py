# Copyright 2020 Google Inc
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

"""Listing available workers."""

from typing import Type, TypeVar

from jobs.workers import commenter
from jobs.workers import worker
from jobs.workers.bigquery import bq_ml_trainer
from jobs.workers.bigquery import bq_query_launcher
from jobs.workers.bigquery import bq_script_executor
from jobs.workers.bigquery import bq_to_measurement_protocol_ga4
from jobs.workers.bigquery import bq_to_storage_exporter
from jobs.workers.bigquery import bq_to_vertexai_dataset
from jobs.workers.bigquery import bq_waiter
from jobs.workers.bigquery import storage_to_bq_importer
from jobs.workers.ga import ga_audiences_updater
from jobs.workers.ga import ga_audiences_updater_ga4
from jobs.workers.ga import ga_custom_dimension_creator_ga4
from jobs.workers.ga import ga_data_importer
from jobs.workers.ga import ga_waiter
from jobs.workers.storage import storage_cleaner
from jobs.workers.vertexai import vertexai_batch_predictor_to_bq
from jobs.workers.vertexai import vertexai_tabular_trainer
from jobs.workers.vertexai import vertexai_waiter
from jobs.workers.vertexai import vertexai_worker

ConcreteWorker = TypeVar('ConcreteWorker', bound=worker.Worker)

WORKERS_MAPPING = {
    # 'AutoMLImporter',
    # 'AutoMLPredictor',
    # 'AutoMLTrainer',
    'BQMLTrainer':
        bq_ml_trainer.BQMLTrainer,
    'BQQueryLauncher':
        bq_query_launcher.BQQueryLauncher,
    'BQScriptExecutor':
        bq_script_executor.BQScriptExecutor,
    # 'BQToAppConversionAPI',
    # 'BQToCM',
    # 'BQToMeasurementProtocol',
    'BQToMeasurementProtocolGA4':
        bq_to_measurement_protocol_ga4.BQToMeasurementProtocolGA4,
    'BQToStorageExporter':
        bq_to_storage_exporter.BQToStorageExporter,
    'BQToVertexAIDataset':
        bq_to_vertexai_dataset.BQToVertexAIDataset,
    'Commenter':
        commenter.Commenter,
    'GAAudiencesUpdater':
        ga_audiences_updater.GAAudiencesUpdater,
    'GA4AudiencesUpdater':
        ga_audiences_updater_ga4.GA4AudiencesUpdater,
    'GA4CustomDimensionCreator':
        ga_custom_dimension_creator_ga4.GA4CustomDimensionCreator,
    'GADataImporter':
        ga_data_importer.GADataImporter,
    # 'GAToBQImporter',
    # 'MLPredictor',
    # 'MLTrainer',
    # 'MLVersionDeployer',
    # 'StorageChecker',
    'StorageCleaner':
        storage_cleaner.StorageCleaner,
    'StorageToBQImporter':
        storage_to_bq_importer.StorageToBQImporter,
    'VertexAIBatchPredictorToBQ':
        vertexai_batch_predictor_to_bq.VertexAIBatchPredictorToBQ,
    'VertexAITabularTrainer':
        vertexai_tabular_trainer.VertexAITabularTrainer,
}

_PRIVATE_WORKERS_MAPPING = {
    'BQToMeasurementProtocolProcessorGA4':
        bq_to_measurement_protocol_ga4.BQToMeasurementProtocolProcessorGA4,
    'BQWaiter': bq_waiter.BQWaiter,
    'GADataImportUploadWaiter': ga_waiter.GADataImportUploadWaiter,
    'VertexAIWaiter': vertexai_waiter.VertexAIWaiter,
    'VertexAIWorker': vertexai_worker.VertexAIWorker,
}


def get_worker_class(class_name: str) -> Type[ConcreteWorker]:
  """Returns a worker class.

  Args:
    class_name: The name of the worker class.

  Raises:
    ModuleNotFoundError: if the class name cannot be found.
  """
  for name in WORKERS_MAPPING:
    if class_name.lower() == name.lower():
      return WORKERS_MAPPING[name]
  for name in _PRIVATE_WORKERS_MAPPING:
    if class_name.lower() == name.lower():
      return _PRIVATE_WORKERS_MAPPING[name]
  raise ModuleNotFoundError
