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
project_id = "PROJECT_ID"
project_region = "europe-west"

# Directory on your space to deploy
# NB: if kept empty this will defaults to /tmp/<project_id_gae>
workdir = ""

# Database config
database_name = "DB_NAME"
database_username = "DB_USERNAME"
database_password = "DB_PASSWORD"
database_instance_name = "DB_INSTANCE_NAME"
database_backup_enabled = "True"
database_ha_type = "DB_HA_TYPE"
database_region = "DB_REGION"
database_tier = "DB_TIER"
database_project = "DB_PROJECT"

# PubSub config
pubsub_verification_token = "PUBSUB_TOKEN"

# Sender email for notifications
notification_sender_email = "NOTIF_SENDER_EMAIL"

# AppEngine config
gae_app_title = "GAE_APP_TITLE"
gae_project = "GAE_PROJECT"
gae_region = "GAE_REGION"

# Enable flag for looking of pipelines on other stages
# Options: True, False
enabled_stages = False

# Network configuration
use_vpc = False
network = "NETWORK"
subnet = "SUBNET"
subnet_region = "SUBNET_REGION"
subnet_cidr = "SUBNET_CIDR"
connector = "CONNECTOR"
connector_subnet = "CONNECTOR_SUBNET"
connector_cidr = "CONNECTOR_CIDR"
connector_min_instances = "CONNECTOR_MIN_INSTANCES"
connector_max_instances = "CONNECTOR_MAX_INSTANCES"
connector_machine_type = "CONNECTOR_MACHINE_TYPE"
network_project = "NETWORK_PROJECT"
