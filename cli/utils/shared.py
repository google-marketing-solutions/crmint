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
import subprocess
import sys
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
  command = f'{GCLOUD} config get-value project 2>/dev/null'
  status, out, _ = execute_command(
      'Get current project identifier',
      command,
      debug=debug,
      debug_uses_std_out=False)
  if status != 0:
    sys.exit(status)
  return out.strip()


def activate_apis(debug: bool = False) -> None:
  """
  Args:
    debug: Flag to enable debug mode outputs.
  """
  cmd = f'{GCLOUD} services enable run.googleapis.com'
  execute_command('Activate Cloud services', cmd, debug=debug)


def get_default_stage_path(debug: bool = False) -> pathlib.Path:
  """Returns the default stage file path, derived from the GCP project name.

  Args:
    debug: Flag to enable debug mode outputs.
  """
  project_id = get_current_project_id(debug=debug)
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
  with open(stage_path, 'w+') as fp:
    json.dump(context.__dict__, fp)


def check_variables():
  # Google Cloud SDK
  if not os.environ.get('GOOGLE_CLOUD_SDK', None):
    gcloud_path = subprocess.Popen(
        'gcloud --format="value(installation.sdk_root)" info',
        shell=True,
        stdout=subprocess.PIPE)
    out = gcloud_path.communicate()[0]
    os.environ['GOOGLE_CLOUD_SDK'] = out.decode('utf-8').strip()


def get_region(project_id: ProjectId) -> str:
  """Returns a Cloud Scheduler compatible region.

  Cloud Scheduler is the limiting factor for picking up a cloud region as it
  is not available in all Cloud Run available regions.

  Args:
    project_id: GCP project identifier.
  """
  cmd = f'{GCLOUD} scheduler locations list --format="value(locationId)"'
  _, out, _ = execute_command(
      'Get available Compute regions', cmd, debug_uses_std_out=False)
  regions = out.strip().split('\n')
  for i, region in enumerate(regions):
    click.echo(f'{i + 1}) {region}')
  i = -1
  while i < 0 or i >= len(regions):
    i = click.prompt(
        'Enter an index of the region to deploy CRMint in', type=int) - 1
  region = regions[i].strip()
  return region


def default_stage_context(project_id: ProjectId,
                          gcloud_account_email: str) -> StageContext:
  """Returns a stage context initialized with default settings.

  Args:
    project_id: GCP project identifier.
    gcloud_account_email: Email account running CloudShell.
  """
  region = settings.REGION or get_region(project_id)
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
