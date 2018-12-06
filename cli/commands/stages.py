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

import os
import random
import string

import click

from cli.utils import constants
from cli.utils import shared


STAGE_FILE_TEMPLATE = """
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
service_account_file = "{service_account_file}"

# Project ID in Google Cloud
project_id_gae = "{project_id_gae}"

# Region. Use `gcloud app regions list` to list available regions.
project_region = "{project_region}"

# Machine Type. Use `gcloud sql tiers list` to list available machine types.
project_sql_tier = "{project_sql_tier}"

# SQL region. Use `gcloud sql regions list` to list available regions.
project_sql_region = "{project_sql_region}"

# Directory on your space to deploy
# NB: if kept empty this will defaults to /tmp/<project_id_gae>
workdir = "{workdir}"

# Database name
db_name = "{db_name}"

# Database username
db_username = "{db_username}"

# Database password
db_password = "{db_password}"

# Database instance name
db_instance_name = "{db_instance_name}"

# Sender email for notifications
notification_sender_email = "{notification_sender_email}"

# Title name for application
app_title = "{app_title}"

# Enable flag for looking of pipelines on other stages
# Options: True, False
enabled_stages = False

""".strip()


def _create_stage_file(stage_name):
  filename = "{}.py".format(stage_name)
  filepath = os.path.join(constants.STAGE_DIR, filename)

  # Generates a cryptographically secured random password for the database user.
  # Source: https://stackoverflow.com/a/23728630
  random_password = ''.join(random.SystemRandom().choice(
      string.ascii_lowercase + string.digits) for _ in range(16))

  content = STAGE_FILE_TEMPLATE.format(
      service_account_file="{}.json".format(stage_name),
      project_id_gae=stage_name,
      project_region="europe-west",
      project_sql_region="europe-west1",
      project_sql_tier="db-g1-small",
      workdir="/tmp/{}".format(stage_name),
      db_name="crmintapp",
      db_username="crmintapp",
      db_password=random_password,
      db_instance_name="crmintapp",
      notification_sender_email="noreply@{}.appspotmail.com".format(stage_name),
      app_title=" ".join(stage_name.split("-")).title(),
  )
  with open(filepath, 'w+') as fp:
    fp.write(content)
  return filepath

@click.group()
def cli():
  """Manage multiple instances of CRMint"""
  pass


@cli.command('create')
@click.option('--stage_name', default=None)
def create(stage_name):
  """Create new project in Google Cloud and add instances"""
  if not stage_name:
    stage_name = shared.get_default_stage_name()

  if shared.check_stage_file(stage_name):
    click.echo(click.style("This stage name already exists. You can list "
                           "them all with: `$ crmint stages list`", fg='red', bold=True))
    exit(1)

  filepath = _create_stage_file(stage_name)
  click.echo(click.style("Stage file created: %s" % filepath, fg='green'))


def _ignore_stage_file(file_name):
  IGNORED_STAGE_FILES = ["__init__.py"]
  ENDS_WITH = [".pyc", ".example"]
  return file_name in IGNORED_STAGE_FILES or file_name.endswith(tuple(ENDS_WITH))


@cli.command('list')
def list_stages():
  """List your stages defined in cli/stages directory"""
  for file_name in os.listdir(constants.STAGE_DIR):
    if not _ignore_stage_file(file_name):
      click.echo(file_name[:-3])
