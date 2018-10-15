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
# import sys
# sys.path.append("/usr/local/google/home/ldiana/projects/crmint/cli")

import os
from glob import glob
import subprocess
import click
from crmint_commands import _constants
from crmint_commands import _utils


FRONTEND_SUCCESS_MESSAGE = "\rFrontend deployed successfully!            "


def _get_stage_file(stage):
  stage_file = "{}/{}.py".format(_constants.STAGE_DIR, stage)
  return stage_file


def _check_stage_file(stage):
  stage_file = _get_stage_file(stage)
  if not os.path.isfile(stage_file):
    click.echo("\nStage file '%s' not found." % stage)
    return False
  return True


def _get_stage_object(stage_name):
  return getattr(__import__("stage_variables.%s" % stage_name), stage_name)


def source_stage_file_and_command_script(stage_file, command):
  os.system("""SCRIPTS_DIR="{}"
        source \"{}\"
        source \"{}/deploy/before_hook.sh\"
        source \"{}/deploy/{}.sh\""""
            .format(_constants.SCRIPTS_DIR, stage_file,
                    _constants.SCRIPTS_DIR,
                    _constants.SCRIPTS_DIR, command))


def deploy_frontend(stage):
  try:
    gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet --project"
    deploy_commands = ("npm install",
                       "node_modules/@angular/cli/bin/ng build --prod",
                       "{} {} app deploy gae.yaml --version=v1".format(gcloud_command,
                                                                       stage.project_id_gae),
                       "{} {} app deploy dispatch.yaml".format(gcloud_command,
                                                               stage.project_id_gae))
    frontend_dir = r"%s/frontend" % stage.workdir
    subprocess.Popen(deploy_commands, cwd=frontend_dir,
                     shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
  except Exception as e:
    raise Exception("Deploy frontend exception: %s" % e.message)


def deploy_ibackend(stage):
  try:
    backends_dir = os.path.join(stage.workdir, "backends")
    # Applying patches required in GAE environment
    # os.mkdir(os.path.join(backends_dir, "lib"))
    for file_name in glob("{}/*.pyc".format(stage.workdir)):
      os.remove(file_name)
    subprocess.Popen(("pip install -r ibackend/requirements.txt -t lib -q",
                      "{}/bin/gcloud --quiet --project {} app deploy gae_ibackend.yaml --version=v1"
                      .format(
                          stage.cloudsql_dir, stage.project_id_gae)
                     ),
                     cwd=backends_dir, shell=True,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
  except Exception as e:
    raise Exception("Deploy ibackend exception: %s" % e.message)



@click.group()
def cli():
  """CRMint Deploy application to Google App Engine"""
  pass


@cli.command('all')
@click.argument('stage_name')
@click.pass_context
def deploy_all(context, stage_name):
  """Deploy all <stage>"""
  deploy_components = [frontend, ibackend] #, jbackend, cron, migration]
  with click.progressbar(deploy_components) as progress_bar:
    for component in progress_bar:
      context.invoke(component, stage_name=stage_name)


@cli.command('frontend')
@click.argument('stage_name')
def frontend(stage_name):
  """Deploy frontend <stage>"""
  if not _check_stage_file(stage_name):
    exit(1)
  click.echo("\nDeploying frontend...", nl=False)
  stage = _get_stage_object(stage_name)
  try:
    click.echo("step 1 out of 2...", nl=False)
    stage = _utils.before_hook(stage)
    click.echo("\rstep 2 out of 2...", nl=False)
    deploy_frontend(stage)
    click.echo(FRONTEND_SUCCESS_MESSAGE)
  except Exception as exception:
    click.echo("\nAn error occured: %s" % exception.message)
    exit(1)


@cli.command('ibackend')
@click.argument('stage_name')
def ibackend(stage_name):
  """Deploy ibackend <stage>"""
  click.echo("\nDeploying ibackend...", nl=False)
  stage = _get_stage_object(stage_name)
  if not _check_stage_file(stage_name):
    exit(1)
  try:
    click.echo("step 1 out of 2...", nl=False)
    stage = _utils.before_hook(stage)
  except Exception as exception:
    click.echo("\nAn error occured during step 1 of ibackend deployment: %s" % exception.message)
    exit(1)
  try:
    click.echo("\rstep 2 out of 2...", nl=False)
    deploy_ibackend(stage)
    click.echo("\rIbackend deployed successfully              ")
  except Exception as exception:
    click.echo("\nAn error occured during step 2 of ibackend deployment: %s" % exception.message)
    exit(1)

@cli.command('jbackend')
@click.argument('stage_name')
def jbackend(stage_name):
  """Deploy jbackend <stage>"""
  stage_file = _get_stage_file(stage_name)
  if not _check_stage_file(stage_name):
    exit(1)
  source_stage_file_and_command_script(stage_file, 'jbackend')


@cli.command('migration')
@click.argument('stage_name')
def migration(stage_name):
  """Deploy migration <stage>"""
  stage_file = _get_stage_file(stage_name)
  if not _check_stage_file(stage_name):
    exit(1)
  source_stage_file_and_command_script(stage_file, 'migration')


# [TODO] Make cm and ch options mutual exclusiv
@cli.command('cron')
@click.argument('stage_name')
@click.option('--cron-frequency-minutes', '-m', default=None, show_default=True,
              help='Cron job schedule in minutes')
@click.option('--cron-frequency-hours', '-h', default=None, show_default=True,
              help='Cron job schedule in hours')
def cron(stage_name, cron_frequency_minutes, cron_frequency_hours):
  """Deploy cron file <stage>"""
  if not _check_stage_file(stage_name):
    exit(1)
  stage_file = _get_stage_file(stage_name)
  with open(_constants.CRON_FILE, "w") as cron_file:
    if cron_frequency_minutes is None and cron_frequency_hours is None:
      cron_file.write(_constants.EMPTY_CRON_TEMPLATE)
    else:
      if cron_frequency_minutes:
        cron_file.write(_constants.CRON_TEMPLATE
                        .format(str(cron_frequency_minutes),
                                "minutes"))
      if cron_frequency_hours:
        cron_file.write(_constants.CRON_TEMPLATE
                        .format(str(cron_frequency_hours),
                                "hours"))
  source_stage_file_and_command_script(stage_file, 'cron')


@cli.command('db_seeds')
@click.argument('stage_name')
def db_seeds(stage_name):
  """Add seeds to DB"""
  if not _check_stage_file(stage_name):
    exit(1)
  stage_file = _get_stage_file(stage_name)
  source_stage_file_and_command_script(stage_file, 'db_seeds')


@cli.command('reset_pipeline')
@click.argument('stage_name')
def reset_pipeline(stage_name):
  """Reset Job statuses in Pipeline"""
  stage_file = _get_stage_file(stage_name)
  if not _check_stage_file(stage_name):
    exit(1)
  source_stage_file_and_command_script(stage_file, 'reset_pipeline')


if __name__ == '__main__':
  cli()
