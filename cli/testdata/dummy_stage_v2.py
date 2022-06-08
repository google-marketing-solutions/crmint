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

###
# Variables for stage
###

# Service account json file
service_account_file = "crmint-dummy-v2.json"

# Project ID in Google Cloud
project_id_gae = "crmint-dummy-v2"

# Region. Use `gcloud app regions list` to list available regions.
project_region = "europe-west"

# Machine Type. Use `gcloud sql tiers list` to list available machine types.
project_sql_tier = "db-g2-small"

# SQL region. Use `gcloud sql regions list` to list available regions.
project_sql_region = "europe-west1"

# Directory on your space to deploy
# NB: if kept empty this will defaults to /tmp/<project_id_gae>
workdir = "/tmp/crmint-dummy-v2"

# Database name
db_name = "old_name"

# Database username
db_username = "old_username"

# Database password
db_password = "old_password"

# Database instance name
db_instance_name = "old_instance_name"

# Sender email for notifications
notification_sender_email = "noreply@crmint-dummy-v2.appspotmail.com"

# Title name for application
app_title = "Crmint Dummy v2"

# Enable flag for looking of pipelines on other stages
# Options: True, False
enabled_stages = False
