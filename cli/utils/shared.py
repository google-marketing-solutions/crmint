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

"""Package for shared methods among the commands."""

import json
import os
import pathlib
import re
import subprocess
import textwrap
import types
from typing import Callable, NewType, Tuple, Union

import click

from cli.utils import constants
from cli.utils import settings
from cli.utils import spinner
from cli.utils.constants import GCLOUD

ProjectId = NewType('ProjectId', str)
StageContext = NewType('StageContext', types.SimpleNamespace)

_INDENT_PREFIX = '     '


def execute_command(step_name: str,
                    command: Union[str, Callable[[], Tuple[int, str, str]]],
                    cwd: str = '.',
                    capture_outputs: bool = False,
                    report_empty_err: bool = True,
                    debug: bool = False,
                    debug_uses_std_out: bool = True,
                    force_std_out: bool = False) -> Tuple[int, str, str]:
  """Runs a shell command and captures if needed the standard outputs.

  Args:
    step_name: String to display the name of the step we are running.
    command: Command to run with its options, or a callable.
    cwd: String path representing the current working directory.
    capture_outputs: If true, stdout and stderr will be captured and not sent to
      `click.echo`. Defaults to False.
    report_empty_err: Boolean to disable the reporting of empty errors.
    debug: Boolean to force a more verbose output.
    debug_uses_std_out: Boolean to use stdout and stderr in debug mode, without
      catching the streams in our pipe call.
    force_std_out: Boolean to display everything that the command would have
      displayed if run in a terminal.

  Returns:
    Captures outputs and returns a tuple with `(exit_code, stdout, stderr)`.
  """
  stdout, stderr = subprocess.PIPE, subprocess.PIPE

  if (debug and debug_uses_std_out) or force_std_out:
    stdout, stderr = None, None
  click.secho(f'---> {step_name}', fg='blue', bold=True, nl=debug)
  if debug:
    click.echo(click.style(f'cwd: {cwd}', bg='blue', bold=False))
    click.echo(click.style(f'$ {command}', bg='blue', bold=False))
  with spinner.spinner(disable=debug, color='blue', bold=True):
    if isinstance(command, Callable):
      status, out, err = command()
    else:
      try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            executable='/bin/bash',
            check=True,
            stdout=stdout,
            stderr=stderr)
        status, out, err = result.returncode, result.stdout, result.stderr
      except subprocess.CalledProcessError as e:
        status, out, err = e.returncode, e.stdout, e.stderr
  if isinstance(out, bytes):
    out = out.decode('utf-8')
  if isinstance(err, bytes):
    err = err.decode('utf-8')
  if not debug:
    click.echo('')
  if not debug and capture_outputs:
    return status, out, err
  if status != 0 and (err or report_empty_err):
    click.echo('')
    click.secho(f'Failed step "{step_name}"', fg='red', bold=True)
    click.echo(f'command: {command}')
    click.echo(f'exit code: {status}')
    click.echo('stderr:')
    click.echo(textwrap.indent(err or '<EMPTY>', '  '))
    click.echo('stdout:')
    click.echo(textwrap.indent(out or '<EMPTY>', '  '))
  elif debug and not debug_uses_std_out:
    click.echo('stdout:')
    click.echo(textwrap.indent(out or '<EMPTY>', '  '))
  return status, out, err


def get_current_project_id(debug: bool = False) -> ProjectId:
  """Returns the current configured project Id.

  Args:
    debug: Flag to enable debug mode outputs.
  """
  command = f'{GCLOUD} config list --format="value(core.project)"'
  _, out, _ = execute_command(
      'Get current project identifier',
      command,
      debug=debug,
      debug_uses_std_out=False)
  return out.strip()


def list_user_project_ids(debug: bool = False) -> [ProjectId]:
  """Returns a list of valid project ids the user has access to.

  Args:
    debug: Flag to enable debug mode outputs.
  """
  command = f'{GCLOUD} projects list --format="value(project_id)"'
  _, out, _ = execute_command(
      'List available projects', command, debug=debug)
  return out.strip().split('\n')


def select_project_id(project_id: ProjectId, debug: bool = False) -> None:
  """Configures the gcloud command to use the given project Id.

  Args:
    project_id: The new project Id to set in the gcloud config.
    debug: Flag to enable debug mode outputs.
  """
  command = f'{GCLOUD} config set project {project_id}'
  execute_command('Configure gcloud with new Project Id', command, debug=debug)


def activate_apis(debug: bool = False) -> None:
  """Activates Cloud Services APIs.

  Args:
    debug: Flag to enable debug mode outputs.
  """
  services = [
      'run.googleapis.com',
      'cloudscheduler.googleapis.com',
  ]
  formatted_services = ' '.join(services)
  cmd = f'{GCLOUD} services enable {formatted_services}'
  execute_command('Activate Cloud services', cmd, debug=debug)


def get_default_stage_path(debug: bool = False) -> pathlib.Path:
  """Returns the default stage file path, derived from the GCP project name.

  Args:
    debug: Flag to enable debug mode outputs.
  """
  project_id = get_current_project_id(debug=debug)
  while not project_id:
    new_project_id = click.prompt(
        textwrap.indent('Enter your Cloud Project ID', _INDENT_PREFIX),
        type=str).strip()
    allowed_project_ids = list_user_project_ids(debug=debug)
    if new_project_id in allowed_project_ids:
      msg = textwrap.indent(
          f'Allowed to access Project ID "{new_project_id}"', _INDENT_PREFIX)
      click.echo(click.style(msg, fg='green', bold=True))
      project_id = ProjectId(new_project_id)
      select_project_id(project_id, debug=debug)
    else:
      msg = textwrap.indent(
          f'Not allowed to access Project ID: {new_project_id}', _INDENT_PREFIX)
      click.echo(click.style(msg, fg='red', bold=True))
  click.echo(textwrap.indent(f'Project ID found: {project_id}', _INDENT_PREFIX))
  return pathlib.Path(constants.STAGE_DIR, f'{project_id}.tfvars.json')


def load_stage(stage_path: pathlib.Path) -> StageContext:
  """Loads stage by interpreting Terraform variables as Python code."""
  with open(stage_path, 'rb') as fp:
    context = json.load(fp)
  stage = types.SimpleNamespace(**context)
  return stage


def create_stage_file(stage_path: pathlib.Path, context: StageContext) -> None:
  """Saves the given context into the given path file."""
  if hasattr(context, 'stage_path'):
    del context.stage_path
  with open(stage_path, 'w+') as fp:
    json.dump(context.__dict__, fp, indent=2)


class CannotFetchStageError(Exception):
  """Raised when the stage file cannot be fetched."""


def fetch_stage_or_default(
    stage_path: Union[None, pathlib.Path],
    debug: bool = False) -> StageContext:
  """Returns the loaded stage context.

  Args:
    stage_path: Stage path to load. If None a default stage path is used.
    debug: Enables the debug mode on system calls.

  Raises:
    CannotFetchStageError: if the stage file can be fetched.
  """
  if not stage_path:
    stage_path = get_default_stage_path(debug=debug)
  if not stage_path.exists():
    click.secho(f'Stage file not found at path: {stage_path}',
                fg='red',
                bold=True)
    click.secho('Fix this by running: $ crmint stages create', fg='green')
    raise CannotFetchStageError(f'Not found at: {stage_path}')

  stage = load_stage(stage_path)
  stage.stage_path = stage_path
  return stage


def check_variables():
  # Google Cloud SDK
  if not os.environ.get('GOOGLE_CLOUD_SDK', None):
    gcloud_path = subprocess.Popen(
        'gcloud --format="value(installation.sdk_root)" info',
        shell=True,
        stdout=subprocess.PIPE)
    out = gcloud_path.communicate()[0]
    os.environ['GOOGLE_CLOUD_SDK'] = out.decode('utf-8').strip()


def get_user_email(debug: bool = False) -> str:
  """Returns the user email configured in the gcloud config.

  Args:
    debug: Enables the debug mode on system calls.
  """
  cmd = f'{GCLOUD} config list --format="value(core.account)"'
  _, out, _ = execute_command(
      'Retrieve gcloud current user',
      cmd,
      debug=debug,
      debug_uses_std_out=False)
  return out.strip()


def get_region(debug: bool = False) -> str:
  """Returns a Cloud Scheduler compatible region.

  Cloud Scheduler is the limiting factor for picking up a cloud region as it
  is not available in all Cloud Run available regions.

  Args:
    debug: Flag to enable debug mode outputs.
  """
  cmd = f'{GCLOUD} scheduler locations list --format="value(locationId)"'
  _, out, _ = execute_command(
      'Get available Compute regions',
      cmd,
      debug_uses_std_out=False,
      debug=debug)
  regions = out.strip().split('\n')
  for i, region in enumerate(regions):
    click.echo(textwrap.indent(f'{i + 1}) {region}', _INDENT_PREFIX))
  i = -1
  while i < 0 or i >= len(regions):
    i = click.prompt(
        textwrap.indent('Enter an index of the region to deploy CRMint in',
                        _INDENT_PREFIX),
        type=int) - 1
  region = regions[i].strip()
  return region


def default_stage_context(*,
                          project_id: ProjectId,
                          region: str,
                          gcloud_account_email: str) -> StageContext:
  """Returns a stage context initialized with default settings.

  Args:
    project_id: GCP project identifier.
    region: GCP region (compatible with Cloud Run and Cloud Scheduler).
    gcloud_account_email: Email account running CloudShell.
  """
  app_title = settings.APP_TITLE or ' '.join(project_id.split('-')).title()
  namespace = types.SimpleNamespace(
      app_title=app_title,
      notification_sender_email=gcloud_account_email,
      iap_support_email=gcloud_account_email,
      iap_allowed_users=[f'user:{gcloud_account_email}'],
      project_id=project_id,
      region=region,
      use_vpc=settings.USE_VPC,
      database_tier=settings.DATABASE_TIER,
      database_availability_type=settings.DATABASE_HA_TYPE,
      frontend_image=settings.FRONTEND_IMAGE,
      controller_image=settings.CONTROLLER_IMAGE,
      jobs_image=settings.JOBS_IMAGE)
  return StageContext(namespace)


def detect_settings_envs():
  """Returns the list of env variables overriding settings defaults."""
  settings_envs = [key for key in os.environ if hasattr(settings, key)]
  click.secho('---> Detect env variables', fg='blue', bold=True, nl=True)
  for varname in settings_envs:
    value = os.getenv(varname)
    click.echo(textwrap.indent(f'{varname}={value}', _INDENT_PREFIX))


def resolve_image_with_digest(image_uri: str, debug: bool = False):
  """Returns the image with its SHA256 digest, given an image URI.

  Args:
    image_uri: Fully-qualified image URI.
    debug: Flag to enable debug mode outputs.
  """
  cmd = textwrap.dedent(f"""\
      {GCLOUD} --verbosity=none container images describe {image_uri} \\
          --format="value(image_summary.fully_qualified_digest)"
      """)
  _, out, _ = execute_command(
      f'Retrieve digest for image: {image_uri}',
      cmd,
      debug=debug,
      debug_uses_std_out=False)
  image_with_digest = out.strip()
  click.echo(textwrap.indent(image_with_digest, _INDENT_PREFIX))
  return image_with_digest


def list_available_tags(image_uri: str, debug: bool = False):
  """Returns a list of available tags to update CRMint to.

  Args:
    image_uri: Image URI (with or without a tag)
    debug: Flag to enable debug mode outputs.
  """
  image_uri_without_tag = image_uri.split(':')[0]
  cmd = textwrap.dedent(f"""\
      {GCLOUD} container images list-tags {image_uri_without_tag} \\
          --filter "tags:*" \\
          --format="value(tags)" \\
          --sort-by=~timestamp
      """)
  _, out, _ = execute_command(
      'List available tags for CRMint',
      cmd,
      debug=debug,
      debug_uses_std_out=False)
  tags = out.strip().replace('\n', ',').split(',')
  return tags


def filter_versions_from_tags(tags: list[str]) -> list[str]:
  """Filters a list of tags to return a list of versions."""
  return [tag for tag in tags if re.fullmatch(r'[\d\.]+', tag)]
