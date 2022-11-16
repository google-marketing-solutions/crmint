#
# Copyright 2022 Google Inc
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

##
# Application config

app_title = "Dummy Project without VPC"
notification_sender_email = "user@example.com"

##
# Security (IAP)

iap_support_email = "user@example.com"

# List of authorized users to open the app.
iap_allowed_users = [
    "user@example.com",
]

###
# Google Cloud Project

project_id = "dummy_project_with_vpc"
region = "europe-west1"

##
# Virtual Private Cloud (more settings in `terraform/variables.tf`)

use_vpc = false

##
# Database (more settings in `terraform/variables.tf`)

database_tier = "db-g1-small"
database_availability_type = "ZONAL"

##
# Services Docker images

frontend_image = "frontend:latest"
controller_image = "controller:latest"
jobs_image = "jobs:latest"

##
# Custom domain

# Automatically configures the load-balancer, routing and
# SSL certificate for your own domain. You will only have to add a DNS
# A record pointing from the load-balancer ip-address to your custom domain.
custom_domain = ""
