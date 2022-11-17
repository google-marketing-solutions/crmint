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

GCLOUD = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"

PROJECT_DIR = pathlib.Path(
    os.path.dirname(__file__), "../..").resolve().as_posix()
STAGE_DIR = "{}/cli/stages".format(PROJECT_DIR)

TFVARS_FILE_TEMPLATE = textwrap.dedent("""\
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

    app_title = "{ctx.app_title}"
    notification_sender_email = "{ctx.iap_support_email}"

    ##
    # Security (IAP)

    iap_support_email = "{ctx.iap_support_email}"

    # List of authorized users to open the app.
    iap_allowed_users = [
        "user:{ctx.iap_support_email}",
    ]

    ###
    # Google Cloud Project

    project_id = "{ctx.project_id}"
    region = "{ctx.region}"

    ##
    # Virtual Private Cloud (more settings in `terraform/variables.tf`)

    use_vpc = {ctx.use_vpc_tfvar_boolean}

    ##
    # Database (more settings in `terraform/variables.tf`)

    database_tier = "{ctx.database_tier}"
    database_availability_type = "{ctx.database_availability_type}"

    ##
    # Services Docker images

    frontend_image = "{ctx.frontend_image}"
    controller_image = "{ctx.controller_image}"
    jobs_image = "{ctx.jobs_image}"

    ##
    # Custom domain

    # Automatically configures the load-balancer, routing and
    # SSL certificate for your own domain. You will only have to add a DNS
    # A record pointing from the load-balancer ip-address to your custom domain.
    custom_domain = ""

    """)
