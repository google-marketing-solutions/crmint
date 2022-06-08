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

import importlib
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap
import types
from typing import NewType, Tuple

import click

from cli.utils import constants
from cli.utils import spinner
from cli.utils.constants import GCLOUD

ProjectId = NewType('ProjectId', str)
StageContext = NewType('StageContext', types.SimpleNamespace)

_INDENT_PREFIX = '     '


def execute_command(step_name: str,
                    command: str,
                    cwd: str = '.',
                    report_empty_err: bool = True,
                    debug: bool = False,
                    debug_uses_std_out: bool = True,
                    force_std_out: bool = False) -> Tuple[int, str, str]:
  """Runs a shell command and captures if needed the standard outputs.

  Args:
    step_name: String to display the name of the step we are running.
    command: String representation of the command to run with its options.
    cwd: String path representing the current working directory.
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
    try:
      result = subprocess.run(
          command,
          cwd=cwd,
          shell=True,
          executable='/bin/sh',
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
  if debug and not debug_uses_std_out:
    click.echo(f'stdout: {out}')
  if status != 0 and (err or report_empty_err):
    click.echo('')
    click.secho(f'Failed step "{step_name}"', fg='red', bold=True)
    click.echo(f'command: {command}')
    click.echo(f'exit code: {status}')
    click.echo(f'stderr: {err}')
    click.echo(f'stdout: {out}')
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


def get_default_stage_path(debug: bool = False) -> pathlib.Path:
  """Returns the default stage file path, derived from the GCP project name.

  Args:
    debug: Flag to enable debug mode outputs.
  """
  project_id = get_current_project_id(debug=debug)
  click.echo(textwrap.indent(f'Project ID found: {project_id}', _INDENT_PREFIX))
  return pathlib.Path(constants.STAGE_DIR, f'{project_id}.py')


def load_stage(stage_path: pathlib.Path) -> StageContext:
  spec = importlib.util.spec_from_file_location('loaded_stage', stage_path)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  context = dict(
      (x, getattr(module, x)) for x in dir(module) if not x.startswith('__'))
  return types.SimpleNamespace(**context)


def before_hook(stage: types.ModuleType) -> types.ModuleType:
  """Adds variables to the stage object."""
  # Working directory to prepare deployment files.
  if not stage.workdir:
    stage.workdir = '/tmp/{}'.format(stage.project_id)

  # Set DB connection variables.
  stage.db_instance_conn_name = '{}:{}:{}'.format(
      stage.database_project,
      stage.database_region,
      stage.database_instance_name)

  stage.cloudsql_dir = '/tmp/cloudsql'
  stage.cloud_db_uri = 'mysql+mysqlconnector://{}:{}@/{}?unix_socket=/cloudsql/{}'.format(
      stage.database_username,
      stage.database_password,
      stage.database_name,
      stage.db_instance_conn_name)

  stage.local_db_uri = 'mysql+mysqlconnector://{}:{}@/{}?unix_socket={}/{}'.format(
      stage.database_username,
      stage.database_password,
      stage.database_name,
      stage.cloudsql_dir,
      stage.db_instance_conn_name)

  # Cleans the working directory.
  target_dir = stage.workdir
  try:
    if os.path.exists(target_dir):
      shutil.rmtree(target_dir)
  except Exception as e:
    raise Exception(f'Stage 1 error when copying to workdir: {e}') from e

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
