# Copyright 2018 Google Inc
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
"""
	Constants used in the crmint_commands package
"""
import os


PROJECT_DIR = os.path.join(os.path.dirname(__file__), '../../..')
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
BACKENDS_DIR = os.path.join(PROJECT_DIR, "backends")
SCRIPTS_DIR = "{}/scripts".format(PROJECT_DIR)
STAGE_DIR = "{}/cli/stage_variables".format(PROJECT_DIR)

STAGE_EXAMPLE_PATH = "{}/stage_name.py.example".format(STAGE_DIR)

SERVICE_ACCOUNT_PATH = "{}/backends/data/".format(PROJECT_DIR)
SERVICE_ACCOUNT_DEFAULT_FILE_NAME = "service-account.json"


TASKS_PATH = "{}/cli/crmint_commands/".format(PROJECT_DIR)
SEEDS_TASK = "_task_db_seeds.py"


REQUIREMENTS_DIR = os.path.join(PROJECT_DIR, "cli/requirements.txt")
LIB_DEV_PATH = os.path.join(PROJECT_DIR, "backends/lib_dev")


CRON_FILE = "{}/backends/cron.yaml".format(PROJECT_DIR)

CRON_TEMPLATE = """# Copyright 2018 Google Inc
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

cron:
- description: cron service handler
  url: /cron
  schedule: every {} {}
  target: job-service
"""


EMPTY_CRON_TEMPLATE = """# Copyright 2018 Google Inc
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
cron:
"""
