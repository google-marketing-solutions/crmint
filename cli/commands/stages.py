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

"""Command line to manage stage files."""

import pathlib
import sys
import types
from typing import Union

import click

from cli.utils import constants
from cli.utils import shared

SUPPORTED_STAGE_VERSIONS = (
    constants.STAGE_VERSION_1_0,
    constants.STAGE_VERSION_2_0,
    constants.STAGE_VERSION_3_0
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


def _detect_stage_version(stage_path: pathlib.Path) -> constants.SpecVersion:
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
    if stage.spec_version not in SUPPORTED_STAGE_VERSIONS:
      raise ValueError(f'Unsupported spec version: "{stage.spec_version}". '
                       f'Supported versions are {SUPPORTED_STAGE_VERSIONS}')
    return stage.spec_version

  stage_bash_filename = f'{stage_path.stem}.sh'
  stage_bash_filepath = pathlib.Path(
      constants.PROJECT_DIR, 'scripts/variables/stages', stage_bash_filename)
  if stage_bash_filepath.exists():
    return constants.STAGE_VERSION_1_0

  raise ValueError(f'Stage file not found neither at path: "{stage_path}" '
                   f'nor at path: {stage_bash_filepath}')


def _parse_stage_file(stage_path: pathlib.Path) -> shared.StageContext:
  stage_version = _detect_stage_version(stage_path)
  if stage_version == constants.STAGE_VERSION_1_0:
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
@click.option('--debug/--no-debug', default=False)
def create(stage_path: Union[None, str], debug: bool) -> None:
  """Create new stage file."""
  click.echo(click.style('>>>> Create stage', fg='magenta', bold=True))

  if not stage_path:
    stage_path = shared.get_default_stage_path()
  else:
    stage_path = pathlib.Path(stage_path)

  if stage_path.exists():
    click.echo(click.style(f'This stage file "{stage_path}" already exists. '
                           f'List them all with: `$ crmint stages list`.',
                           fg='red',
                           bold=True))
  else:
    project_id = shared.get_current_project_id(debug=debug)
    context = shared.default_stage_context(project_id)
    shared.create_stage_file(stage_path, context)
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
@click.option('--debug/--no-debug', default=False)
def migrate(stage_path: Union[None, str], debug: bool) -> None:
  """Migrate old stage file format to the latest one."""
  click.echo(click.style('>>>> Migrate stage', fg='magenta', bold=True))

  if not stage_path:
    stage_path = shared.get_default_stage_path(debug=debug)

  stage_version = _detect_stage_version(stage_path)
  if stage_version == constants.LATEST_STAGE_VERSION:
    click.echo(click.style(
        f'Already latest version detected: {stage_path}', fg='green'))
    return

  try:
    old_context = _parse_stage_file(stage_path)
  except ValueError as inst:
    click.echo(click.style(str(inst), fg='red', bold=True))
    sys.exit(1)

  # Save the new stage
  project_id = shared.get_current_project_id(debug=debug)
  new_context = shared.default_stage_context(project_id)
  # NOTE: Variable names are identical in spec v1 and v2
  for key_v3, key_v2 in MAPPING_v3_from_v2.items():
    setattr(new_context, key_v3, getattr(old_context, key_v2))
  shared.create_stage_file(stage_path, new_context)
  click.echo(click.style(
      f'Successfully migrated stage file at: {stage_path}', fg='green'))
