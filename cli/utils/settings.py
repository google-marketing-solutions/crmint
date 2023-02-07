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

APP_TITLE = os.getenv('APP_TITLE', None)
REGION = os.getenv('REGION', None)
USE_VPC = bool(int(os.getenv('USE_VPC', '1')))
DATABASE_INSTANCE_NAME = os.getenv('DATABASE_INSTANCE_NAME', 'crmint-3-db')
DATABASE_TIER = os.getenv('DATABASE_TIER', 'db-g1-small')
DATABASE_HA_TYPE = os.getenv('DATABASE_HA_TYPE', 'ZONAL')

CRMINT_VERSION = os.getenv('CRMINT_VERSION', 'master')

FRONTEND_IMAGE = os.getenv(
    'FRONTEND_IMAGE',
    f'europe-docker.pkg.dev/instant-bqml-demo-environment/crmint/frontend:{CRMINT_VERSION}'
)
CONTROLLER_IMAGE = os.getenv(
    'CONTROLLER_IMAGE',
    f'europe-docker.pkg.dev/instant-bqml-demo-environment/crmint/controller:{CRMINT_VERSION}'
)
JOBS_IMAGE = os.getenv(
    'JOBS_IMAGE',
    f'europe-docker.pkg.dev/instant-bqml-demo-environment/crmint/jobs:{CRMINT_VERSION}'
)
