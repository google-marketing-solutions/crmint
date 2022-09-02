# Copyright 2021 Google Inc
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

"""CRMint's command line settings."""

import os
import secrets

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (os.getenv('DEBUG', 'False') == 'True')

# Project level configuration
REGION = os.environ.get('REGION', 'us-central1')

# Load variables if available. Otherwise, default to defaults.
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'crmintapp-db')
DATABASE_INSTANCE_NAME = os.environ.get('DATABASE_INSTANCE_NAME', DATABASE_NAME)
DATABASE_USER = os.environ.get('DATABASE_USER', 'crmintapp')
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', secrets.token_hex(16))
DATABASE_BACKUP_ENABLED = os.getenv('DATABASE_BACKUP_ENABLED', 'False')
DATABASE_HA_TYPE = os.getenv('DATABASE_HA_TYPE', 'zonal')
DATABASE_REGION = os.environ.get('DATABASE_REGION', REGION)
DATABASE_TIER = os.environ.get('DATABASE_TIER', 'db-g1-small')
DATABASE_PROJECT = os.environ.get('DATABASE_PROJECT', None)
DATABASE_REGION = os.environ.get('DATABASE_REGION', REGION)

# VPC conf for Cloud SQL with private IP address only.
USE_VPC = (os.getenv('USE_VPC', 'False') == 'True')
NETWORK = os.environ.get('NETWORK', 'crmint-vpc')
NETWORK_PROJECT = os.environ.get('NETWORK_PROJECT', None)
SUBNET_REGION = os.environ.get('SUBNET_REGION', REGION)
CONNECTOR = os.environ.get('CONNECTOR', 'crmint-vpc-connector-01')
CONNECTOR_SUBNET = os.environ.get('CONNECTOR_SUBNET',
                                  'crmint-{}-connector-subnet'.format(REGION))
CONNECTOR_CIDR = os.environ.get('CONNECTOR_CIDR', '10.0.0.0/28')
CONNECTOR_MIN_INSTANCES = os.environ.get('CONNECTOR_MIN_INSTANCES', '2')
CONNECTOR_MAX_INSTANCES = os.environ.get('CONNECTOR_MAX_INSTANCES', '4')
CONNECTOR_MACHINE_TYPE = os.environ.get('CONNECTOR_MACHINE_TYPE', 'e2-micro')

# PubSub
PUBSUB_VERIFICATION_TOKEN = os.environ.get('PUBSUB_VERIFICATION_TOKEN',
                                           secrets.token_hex(32))

# AppEngine config
GAE_PROJECT = os.environ.get('GAE_PROJECT', None)
GAE_REGION = os.environ.get('GAE_REGION', 'us-central')
GAE_APP_TITLE = os.environ.get('GAE_APP_TITLE', None)
