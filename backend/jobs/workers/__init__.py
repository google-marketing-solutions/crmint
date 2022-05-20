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


import importlib
import pkgutil
import sys


EXPOSED = (
    # 'AutoMLImporter',
    # 'AutoMLPredictor',
    # 'AutoMLTrainer',
    'BQMLTrainer',
    'BQQueryLauncher',
    'BQScriptExecutor',
    # 'BQToAppConversionAPI',
    # 'BQToCM',
    # 'BQToMeasurementProtocol',
    'BQToMeasurementProtocolGA4',
    'BQToStorageExporter',
    'Commenter',
    # 'GAAudiencesUpdater',
    # 'GADataImporter',
    # 'GAToBQImporter',
    # 'MLPredictor',
    # 'MLTrainer',
    # 'MLVersionDeployer',
    # 'StorageChecker',
    # 'StorageCleaner',
    'StorageToBQImporter',
)


sys.path.insert(1, 'jobs/workers')


def find(class_name):
  """Finds and returns a worker class."""
  module_names = [
      mi.name for mi in pkgutil.walk_packages(['jobs/workers']) if not mi.ispkg]
  for module_name in module_names:
    filename = module_name.split('.')[-1]
    if filename.replace('_', '') == class_name.lower():
      worker_module = importlib.import_module(module_name)
      return getattr(worker_module, class_name)
  raise ModuleNotFoundError
