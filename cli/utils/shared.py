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
import tempfile
import textwrap
import types
from typing import Any, Callable, NewType, Optional, Tuple, Union

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
  stage = types.SimpleNamespace(**context)
  if not hasattr(stage, 'spec_version'):
    # NOTE: `spec_version` flag was not in the v2 template,
    #       which is why it's defined as the default value.
    stage.spec_version = constants.STAGE_VERSION_2_0
  return stage


def create_stage_file(stage_path: pathlib.Path, context: StageContext) -> None:
  """Saves the given context into the given path file."""
  content = constants.STAGE_FILE_TEMPLATE.format(ctx=context)
  with open(stage_path, 'w+') as fp:
    fp.write(content)


def before_hook(stage: StageContext) -> StageContext:
  """Adds variables to the stage context."""
  if not stage.workdir:
    # NOTE: We voluntarily won't delete the content of this temporary directory
    #       so that debugging can be done. In addition, the directory size
    #       is guaranteed to always be small.
    stage.workdir = tempfile.mkdtemp()

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


def copy_tree(
    src: str,
    dst: str,
    ignore: Optional[Callable[[Any, list[str]], set[str]]] = None) -> None:
  """Copies an entire directory tree to a new location.

  Our implementation mainly differs from `shutil.copytree` because it won't
  preserve permissions from source directories.

  Args:
    src: The source directory to copy files from.
    dst: The destination directory to copy files to.
    ignore: A callable built from `shutil.ignore_patterns(*patterns)`.
  """
  if not os.path.isdir(src):
    raise ValueError(f'Cannot copy tree "{src}": not a directory')

  names = os.listdir(src)
  if ignore is not None:
    ignored_names = ignore(src, names)
  else:
    ignored_names = set()

  os.makedirs(dst, exist_ok=True)

  for name in names:
    if name in ignored_names:
      continue
    src_name = os.path.join(src, name)
    dst_name = os.path.join(dst, name)
    if os.path.isdir(src_name):
      copy_tree(src_name, dst_name, ignore=ignore)
    else:
      shutil.copyfile(src_name, dst_name)


def get_regions(project_id: ProjectId) -> Tuple[str, str]:
  """Returns (region, sql_region) from a given GCP project.

  If no App Engine has been deployed before, prompt the user with choices.

  Args:
    project_id: GCP project identifier.
  """
  cmd = textwrap.dedent(f"""\
      {GCLOUD} app describe --verbosity critical \\
          --project={project_id} | grep locationId
      """)
  status, out, _ = execute_command(
      'Get App Engine region',
      cmd,
      report_empty_err=False,
      debug_uses_std_out=False)
  if status == 0:  # App Engine app had already been deployed in some region.
    region = out.strip().split()[1]
  else:  # Get the list of available App Engine regions and prompt user.
    click.echo('     No App Engine app has been deployed yet.')
    cmd = f'{GCLOUD} app regions list --format="value(region)"'
    _, out, _ = execute_command(
        'Get available App Engine regions', cmd, debug_uses_std_out=False)
    regions = out.strip().split('\n')
    for i, region in enumerate(regions):
      click.echo(f'{i + 1}) {region}')
    i = -1
    while i < 0 or i >= len(regions):
      i = click.prompt(
          'Enter an index of the region to deploy CRMint in', type=int) - 1
    region = regions[i].strip()
  sql_region = region if region[-1].isdigit() else f'{region}1'
  return region, sql_region


def default_stage_context(project_id: ProjectId) -> StageContext:
  """Returns a stage context initialized with default settings.

  Args:
    project_id: GCP project identifier.
  """
  region, sql_region = get_regions(project_id)
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
      use_vpc=settings.USE_VPC,
      network=settings.NETWORK,
      subnet_region=sql_region,
      connector=settings.CONNECTOR,
      connector_subnet='crmint-{}-connector-subnet'.format(region),
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
  return StageContext(namespace)
