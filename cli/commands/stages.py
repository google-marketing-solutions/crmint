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

import pathlib
import sys
import textwrap
import types
from typing import NewType, Tuple, Union

import click

from cli.utils import constants
from cli.utils import settings
from cli.utils import shared
from cli.utils.constants import GCLOUD

SpecVersion = NewType('SpecVersion', str)

STAGE_VERSION_1_0 = SpecVersion('v1.0')
STAGE_VERSION_2_0 = SpecVersion('v2.0')
STAGE_VERSION_3_0 = SpecVersion('v3.0')

LATEST_STAGE_VERSION = STAGE_VERSION_3_0
SUPPORTED_STAGE_VERSIONS = (
    STAGE_VERSION_1_0,
    STAGE_VERSION_2_0,
    STAGE_VERSION_3_0
)

MAPPING_v3_from_v2 = {
    'project_id': 'project_id_gae',
    'project_region': 'project_region',
    'database_tier': 'project_sql_tier',
    'database_region': 'project_sql_region',
    'workdir': 'workdir',
    'database_name': 'db_name',
    'database_username': 'db_username',
    'database_password': 'db_password',
    'database_instance_name': 'db_instance_name',
    'database_project': 'project_id_gae',
    'notification_sender_email': 'notification_sender_email',
    'gae_app_title': 'app_title',
    'gae_project': 'project_id_gae',
    'network_project': 'project_id_gae',
    'enabled_stages': 'enabled_stages',
}

# TODO(dulacp): remove the config `enabled_stages`
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
network = "{ctx.network}"
subnet = "{ctx.subnet}"
subnet_region = "{ctx.subnet_region}"
subnet_cidr = "{ctx.subnet_cidr}"
connector = "{ctx.connector}"
connector_subnet = "{ctx.connector_subnet}"
connector_cidr = "{ctx.connector_cidr}"
connector_min_instances = "{ctx.connector_min_instances}"
connector_max_instances = "{ctx.connector_max_instances}"
connector_machine_type = "{ctx.connector_machine_type}"
network_project = "{ctx.network_project}"

""".strip()


def _get_regions(project_id: shared.ProjectId) -> Tuple[str, str]:
  cmd = f'{GCLOUD} app describe --verbosity critical --project={project_id}'
  cmd += '| grep locationId'
  status, out, _ = shared.execute_command(
      'Get App Engine region', cmd, debug_uses_std_out=False)
  if status == 0:  # App Engine app had already been deployed in some region.
    region = out.strip().split()[1]
  else:  # Get the list of available App Engine regions and prompt user.
    click.echo('     No App Engine app has been deployed yet.')
    cmd = f'{GCLOUD} app regions list --format="value(region)"'
    _, out, _ = shared.execute_command(
        'Get available App Engine regions', cmd, debug_uses_std_out=False)
    regions = out.strip().split('\n')
    for i, region in enumerate(regions):
      click.echo(f'{i + 1}) {region}')
    i = -1
    while i < 0 or i >= len(regions):
      i = click.prompt(
          'Enter an index of the region to deploy CRMint in', type=int) - 1
    region = regions[i]
  sql_region = region if region[-1].isdigit() else f'{region}1'
  return region, sql_region


def _default_stage_context(project_id: shared.ProjectId) -> shared.StageContext:
  region, sql_region = _get_regions(project_id)
  gae_app_title = ' '.join(project_id.split('-')).title()
  namespace = types.SimpleNamespace(
      project_id=project_id,
      project_region=region,
      workdir=f'/tmp/{project_id}',
      database_name=settings.DATABASE_NAME,
      database_region=sql_region,
      database_tier=settings.DATABASE_TIER,
      database_username=settings.DATABASE_USER,
      database_password=settings.DATABASE_PASSWORD,
      database_instance_name=settings.DATABASE_INSTANCE_NAME,
      database_backup_enabled=settings.DATABASE_BACKUP_ENABLED,
      database_ha_type=settings.DATABASE_HA_TYPE,
      database_project=settings.DATABASE_PROJECT or project_id,
      network=settings.NETWORK,
      subnet=settings.SUBNET,
      subnet_region=settings.SUBNET_REGION,
      subnet_cidr=settings.SUBNET_CIDR,
      connector=settings.CONNECTOR,
      connector_subnet=settings.CONNECTOR_SUBNET,
      connector_cidr=settings.CONNECTOR_CIDR,
      connector_min_instances=settings.CONNECTOR_MIN_INSTANCES,
      connector_max_instances=settings.CONNECTOR_MAX_INSTANCES,
      connector_machine_type=settings.CONNECTOR_MACHINE_TYPE,
      network_project=settings.NETWORK_PROJECT or project_id,
      gae_project=settings.GAE_PROJECT or project_id,
      gae_region=region,
      gae_app_title=settings.GAE_APP_TITLE or gae_app_title,
      pubsub_verification_token=settings.PUBSUB_VERIFICATION_TOKEN,
      notification_sender_email=f'noreply@{project_id}.appspotmail.com',
      enabled_stages=False)
  return shared.StageContext(namespace)


def _create_stage_file(stage_path: pathlib.Path,
                       context: shared.StageContext) -> None:
  content = STAGE_FILE_TEMPLATE.format(ctx=context)
  with open(stage_path, 'w+') as fp:
    fp.write(content)


def _detect_stage_version(stage_path: pathlib.Path) -> SpecVersion:
  """Returns the spec version detected for a given stage_path.

  Stage version is defined as:
    - `v1` for bash script stage definitions
    - `v2` for python stage definitions
    - `v3` new python stage definitions with VPC support

  Starts by checking for latest version.

  Args:
    stage_path: Path to the stage file.

  Raises:
    ValueError: if the spec version is unsupported or the path does not exist.
  """
  if stage_path.exists():
    stage = shared.load_stage(stage_path)
    # NOTE: `spec_version` flag was not in the v2 template,
    #       which is why it's defined as the default value.
    stage_version = getattr(stage, 'spec_version', STAGE_VERSION_2_0)
    if stage_version not in SUPPORTED_STAGE_VERSIONS:
      raise ValueError(f'Unsupported spec version: "{stage_version}". '
                       f'Supported versions are {SUPPORTED_STAGE_VERSIONS}')
    return stage_version

  stage_bash_filename = f'{stage_path.stem}.sh'
  stage_bash_filepath = pathlib.Path(
      constants.PROJECT_DIR, 'scripts/variables/stages', stage_bash_filename)
  if stage_bash_filepath.exists():
    return STAGE_VERSION_1_0

  raise ValueError(f'Stage file not found neither at path: "{stage_path}" '
                   f'nor at path: {stage_bash_filepath}')


def _parse_stage_file(stage_path: pathlib.Path) -> shared.StageContext:
  stage_version = _detect_stage_version(stage_path)
  if stage_version == STAGE_VERSION_1_0:
    # Loads bash env variables.
    cmd = f'source {stage_path} && set 2>/dev/null'
    _, out, _ = shared.execute_command(
        'Load bash environment variables',
        cmd,
        cwd=constants.PROJECT_DIR,
        debug_uses_std_out=False)
    # Converts these env vars to dict representation.
    old_stage = types.SimpleNamespace()
    for line in out.split('\n'):
      key, _, value = line.partition('=')
      setattr(old_stage, key, value)
    return shared.StageContext(old_stage)
  else:
    return shared.load_stage(stage_path)


@click.group()
def cli():
  """Manage multiple instances of CRMint."""


@cli.command('create')
@click.option('--stage_path', default=None)
def create(stage_path: Union[None, str]):
  """Create new stage file."""
  if not stage_path:
    stage_path = shared.get_default_stage_path()
  else:
    stage_path = pathlib.Path(stage_path)

  if stage_path.exists():
    click.echo(click.style(f'This stage file "{stage_path}" already exists. '
                           f'List them all with: `$ crmint stages list`.',
                           fg='red',
                           bold=True))
    sys.exit(1)

  project_id = shared.get_current_project_id()
  context = _default_stage_context(project_id)
  _create_stage_file(stage_path, context)
  click.echo(click.style(f'Stage file created: {stage_path}', fg='green'))


@cli.command('list')
@click.option('--stage_dir', default=None)
def list_stages(stage_dir: Union[None, str]):
  """List your stages defined in cli/stages directory."""
  if stage_dir is None:
    stage_dir = constants.STAGE_DIR
  for stage_path in pathlib.Path(stage_dir).glob('*.py'):
    if not stage_path.name.startswith('__'):
      click.echo(stage_path.stem)


@cli.command('migrate')
@click.option('--stage_path', default=None)
def migrate(stage_path: Union[None, str]):
  """Migrate old stage file format to the latest one."""
  if not stage_path:
    stage_path = shared.get_default_stage_path()

  stage_version = _detect_stage_version(stage_path)
  if stage_version == LATEST_STAGE_VERSION:
    click.echo(click.style(
        f'Already latest version detected: {stage_path}', fg='green'))
    sys.exit(0)

  try:
    old_context = _parse_stage_file(stage_path)
  except ValueError as inst:
    click.echo(click.style(str(inst), fg='red', bold=True))
    sys.exit(1)

  # Save the new stage
  project_id = shared.get_current_project_id()
  new_context = _default_stage_context(project_id)
  # NOTE: Variable names are identical in spec v1 and v2
  for key_v3, key_v2 in MAPPING_v3_from_v2.items():
    setattr(new_context, key_v3, getattr(old_context, key_v2))
  _create_stage_file(stage_path, new_context)
  click.echo(click.style(
      f'Successfully migrated stage file at: {stage_path}', fg='green'))
