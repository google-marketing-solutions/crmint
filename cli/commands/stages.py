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
from typing import Union

import click

from cli.utils import constants
from cli.utils import settings
from cli.utils import shared


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
    stage_path = shared.get_default_stage_path(debug=debug)
  else:
    stage_path = pathlib.Path(stage_path)

  if stage_path.exists():
    click.echo(click.style(f'This stage file "{stage_path}" already exists. '
                           f'List them all with: `$ crmint stages list`.',
                           fg='red',
                           bold=True))
  else:
    shared.detect_settings_envs()
    shared.activate_apis(debug=debug)
    project_id = shared.get_current_project_id(debug=debug)
    region = settings.REGION or shared.get_region(debug=debug)
    gcloud_account_email = shared.get_user_email(debug=debug)
    context = shared.default_stage_context(
        project_id=project_id,
        region=region,
        gcloud_account_email=gcloud_account_email)
    shared.create_stage_file(stage_path, context)
    click.echo(click.style(f'Stage file created: {stage_path}', fg='green'))


@cli.command('list')
@click.option('--stage_dir', default=None)
def list_stages(stage_dir: Union[None, str]):
  """List your stages defined in cli/stages directory."""
  if stage_dir is None:
    stage_dir = constants.STAGE_DIR
  for stage_path in sorted(pathlib.Path(stage_dir).glob('*.tfvars.json')):
    click.echo(stage_path.name.removesuffix('.tfvars.json'))


@cli.command('migrate')
@click.option('--stage_path', default=None)
@click.option('--debug/--no-debug', default=False)
def migrate(stage_path: Union[None, str], debug: bool) -> None:
  """Migrate old stage file format to the latest one."""
  del stage_path
  del debug
  click.echo(click.style('Deprecated.', fg='blue', bold=True))


@cli.command('update')
@click.option('--stage_path', default=None)
@click.option('--version', default=None)
@click.option('--debug/--no-debug', default=False)
def update(stage_path: Union[None, str], version: str, debug: bool) -> None:
  """Update CRMint version."""
  click.echo(click.style('>>>> Update CRMint version', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = shared.fetch_stage_or_default(stage_path, debug=debug)
  except shared.CannotFetchStageError:
    sys.exit(1)

  available_tags = shared.list_available_tags(
      stage.controller_image, debug=debug)
  if version is None:
    available_versions = shared.filter_versions_from_tags(available_tags)
    version = available_versions[0]
  elif version not in available_tags:
    available_versions = shared.filter_versions_from_tags(available_tags)
    click.echo(click.style(f'The version "{version}" does not exist. '
                           f'Pick a version from: {available_versions}',
                           fg='red',
                           bold=True))
    sys.exit(1)

  stage.frontend_image = f'{stage.frontend_image.split(":")[0]}:{version}'
  stage.controller_image = f'{stage.controller_image.split(":")[0]}:{version}'
  stage.jobs_image = f'{stage.jobs_image.split(":")[0]}:{version}'
  shared.create_stage_file(stage.stage_path, stage)
  click.echo(click.style(f'Stage updated to version: {version}', fg='green'))


@cli.command('allow-users')
@click.argument('user_emails', type=str)
@click.option('--stage_path', default=None)
@click.option('--debug/--no-debug', default=False)
def allow_users(user_emails: str,
                stage_path: Union[None, str],
                debug: bool) -> None:
  """Allow a list of user emails to access CRMint (separated with a comma)."""
  click.echo(click.style('>>>> Allow new users', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = shared.fetch_stage_or_default(stage_path, debug=debug)
  except shared.CannotFetchStageError:
    sys.exit(1)

  new_iap_users = [f'user:{email}' for email in user_emails.split(',')]
  stage.iap_allowed_users = list(set(stage.iap_allowed_users + new_iap_users))
  shared.create_stage_file(stage.stage_path, stage)
  click.echo(click.style('Stage updated with new IAP users', fg='green'))
