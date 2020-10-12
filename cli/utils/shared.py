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
"""
  Package for shared methods among the commands
"""

import os
import shutil
import subprocess

import click

from cli.utils import constants
from cli.utils import spinner


def execute_command(step_name, command, cwd='.', report_empty_err=True,
                    debug=False, stream_output_in_debug=True, force_std_out=False):
  """
  Wrapper that runs a shell command and captures if needed the standard outputs.

  Args:
    step_name: String to display the name of the step we are running.
    command: String representation of the command to run with its options.
    cwd: String path representing the current working directory.
    report_empty_err: Boolean to disable the reporting of empty errors.
    debug: Boolean to force a more verbose output.
    stream_output_in_debug: Boolean to configure the debug display mode.
    force_std_out: Boolean to display everything that the command would have displayed
        if run in a terminal.
  """
  assert isinstance(command, str)
  pipe_output = (None if (debug and stream_output_in_debug) else subprocess.PIPE)
  if force_std_out:
    pipe_output = None
  click.echo(click.style("---> %s " % step_name, fg='blue', bold=True), nl=debug)
  if debug:
    click.echo(click.style("cwd: %s" % cwd, bg='blue', bold=False))
    click.echo(click.style("$ %s" % command, bg='blue', bold=False))
  with spinner.spinner(disable=debug, color='blue', bold=True):
    pipe = subprocess.Popen(
        command,
        cwd=cwd,
        shell=True,
        executable='/bin/bash',
        stdout=pipe_output,
        stderr=pipe_output)
    out, err = pipe.communicate()
  if not debug:
    click.echo("\n", nl=False)
  if debug and not stream_output_in_debug:
    click.echo(out)
  if pipe.returncode != 0 and err and (len(err) > 0 or report_empty_err):
    msg = "\n%s: %s %s" % (step_name, err, ("({})".format(out) if out else ''))
    click.echo(click.style(msg, fg="red", bold=True))
    click.echo(click.style("Command: %s\n" % command, bold=False))
  return pipe.returncode, out.decode('utf-8'), err.decode('utf-8')


def get_default_stage_name(debug=False):
  """
  Computes the default stage filename, derived from the GCP project name.

  Args:
    debug: Boolean to enable debug mode outputs.
  """
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} config get-value project 2>/dev/null".format(
      gcloud_bin=gcloud_command)
  status, out, err = execute_command("Get current project identifier", command, debug=debug, stream_output_in_debug=False)
  if status != 0:
    exit(1)
  stage_name = out.strip()
  click.echo("     Project ID found: %s" % stage_name)
  return stage_name


def get_stage_file(stage_name):
  stage_file = "{}/{}.py".format(constants.STAGE_DIR, stage_name)
  return stage_file


def check_stage_file(stage_name):
  stage_file = get_stage_file(stage_name)
  if not os.path.isfile(stage_file):
    return False
  return True


def get_stage_object(stage_name):
  return getattr(__import__("stages.%s" % stage_name), stage_name)


def get_service_account_file(stage):
  filename = stage.service_account_file
  service_account_file = os.path.join(constants.SERVICE_ACCOUNT_PATH, filename)
  return service_account_file


def check_service_account_file(stage):
  service_account_file = get_service_account_file(stage)
  if not os.path.isfile(service_account_file):
    return False
  return True


def before_hook(stage, stage_name):
  """
  Adds variables to the stage object.
  """
  stage.stage_name = stage_name

  # Working directory to prepare deployment files.
  if not stage.workdir:
    stage.workdir = "/tmp/{}".format(stage.project_id_gae)

  # Set DB connection variables.
  stage.db_instance_conn_name = "{}:{}:{}".format(
      stage.project_id_gae,
      stage.project_sql_region,
      stage.db_instance_name)

  stage.cloudsql_dir = "/tmp/cloudsql"
  stage.cloud_db_uri = "mysql+mysqlconnector://{}:{}@/{}?unix_socket=/cloudsql/{}".format(
      stage.db_username, stage.db_password,
      stage.db_name, stage.db_instance_conn_name)

  stage.local_db_uri = "mysql+mysqlconnector://{}:{}@/{}?unix_socket={}/{}".format(
      stage.db_username, stage.db_password, stage.db_name,
      stage.cloudsql_dir, stage.db_instance_conn_name)

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
  if not os.environ.get("GOOGLE_CLOUD_SDK", None):
    gcloud_path = subprocess.Popen("gcloud --format='value(installation.sdk_root)' info",
                                   shell=True, stdout=subprocess.PIPE)
    os.environ["GOOGLE_CLOUD_SDK"] = gcloud_path.communicate()[0].decode('utf-8').strip()
