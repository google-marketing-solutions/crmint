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

"""Constants used in the cli/commands package."""

import os
import pathlib
import textwrap
from typing import NewType

GCLOUD = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"

PROJECT_DIR = pathlib.Path(
    os.path.dirname(__file__), "../..").resolve().as_posix()
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
BACKENDS_DIR = os.path.join(PROJECT_DIR, "backends")
STAGE_DIR = "{}/cli/stages".format(PROJECT_DIR)

# TODO(dulacp): remove unused constants
SERVICE_ACCOUNT_PATH = "{}/backends/data/".format(PROJECT_DIR)

REQUIREMENTS_DIR = os.path.join(PROJECT_DIR, "cli/requirements.txt")
LIB_DEV_PATH = os.path.join(PROJECT_DIR, "backends/lib_dev")

SpecVersion = NewType('SpecVersion', str)

STAGE_VERSION_1_0 = SpecVersion('v1.0')
STAGE_VERSION_2_0 = SpecVersion('v2.0')
STAGE_VERSION_3_0 = SpecVersion('v3.0')

LATEST_STAGE_VERSION = STAGE_VERSION_3_0

# TODO(dulacp): remove the config `enabled_stages`
STAGE_FILE_TEMPLATE = textwrap.dedent("""\
    #
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

    # Version of the stage definition
    spec_version = "v3.0"

    ###
    # Variables for stage
    ###

    # Project config
    project_id = "{ctx.project_id}"
    project_region = "{ctx.project_region}"

    # Directory on your space to deploy
    # NB: if kept empty this will defaults to /tmp/<project_id>
    workdir = "{ctx.workdir}"

    # Database config
    database_name = "{ctx.database_name}"
    database_username = "{ctx.database_username}"
    database_password = "{ctx.database_password}"
    database_instance_name = "{ctx.database_instance_name}"
    database_backup_enabled = "{ctx.database_backup_enabled}"
    database_ha_type = "{ctx.database_ha_type}"
    database_region = "{ctx.database_region}"
    database_tier = "{ctx.database_tier}"
    database_project = "{ctx.database_project}"

    # PubSub config
    pubsub_verification_token = "{ctx.pubsub_verification_token}"

    # Sender email for notifications
    notification_sender_email = "{ctx.notification_sender_email}"

    # AppEngine config
    gae_app_title = "{ctx.gae_app_title}"
    gae_project = "{ctx.gae_project}"
    gae_region = "{ctx.gae_region}"

    # Enable flag for looking of pipelines on other stages
    # Options: True, False
    enabled_stages = False

    # Network configuration
    use_vpc = {ctx.use_vpc}
    network = "{ctx.network}"
    subnet_region = "{ctx.subnet_region}"
    connector = "{ctx.connector}"
    connector_subnet = "{ctx.connector_subnet}"
    connector_cidr = "{ctx.connector_cidr}"
    connector_min_instances = "{ctx.connector_min_instances}"
    connector_max_instances = "{ctx.connector_max_instances}"
    connector_machine_type = "{ctx.connector_machine_type}"
    network_project = "{ctx.network_project}"

    """)
