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
import signal
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
  except Exception as exception:
    raise Exception("Deploy frontend exception: %s" % exception.message)


def deploy_backend(stage, backend_prefix):
  try:
    backends_dir = os.path.join(stage.workdir, "backends")
    # Applying patches required in GAE environment
    # os.mkdir(os.path.join(backends_dir, "lib"))
    for file_name in glob("{}/*.pyc".format(stage.workdir)):
      os.remove(file_name)
    subprocess.Popen(("pip install -r ibackend/requirements.txt -t lib -q",
                      "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet --project {} \
                      app deploy gae_{}backend.yaml --version=v1"
                      .format(stage.project_id_gae, backend_prefix)
                     ),
                     cwd=backends_dir, shell=True,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
  except Exception as exception:
    raise Exception("Deploy {}backend exception: {}".format(backend_prefix, exception.message))


def deploy_cron(stage):
  subprocess.Popen("$GOOGLE_CLOUD_SDK/bin/gcloud --quiet --project {} \
                   app deploy cron.yaml".format(stage.project_id_gae),
                   cwd=os.path.join(stage.workdir, "backends"),
                   shell=True, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)


@click.group()
def cli():
  """CRMint Deploy application to Google App Engine"""
  pass


@cli.command('all')
@click.argument('stage_name')
@click.pass_context
def deploy_all(context, stage_name):
  """Deploy all <stage>"""
  deploy_components = [frontend, ibackend, jbackend, cron, migration]
  with click.progressbar(deploy_components) as progress_bar:
    for component in progress_bar:
      context.invoke(component, stage_name=stage_name)


@cli.command('frontend')
@click.argument('stage_name')
def frontend(stage_name):
  """Deploy frontend <stage>"""
  if not _check_stage_file(stage_name):
    click.echo("\nStage file '%s' not found." % stage_name)
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
  stage = _get_stage_object(stage_name)
  if not _check_stage_file(stage_name):
    click.echo("\nStage file '%s' not found." % stage)
    exit(1)
  click.echo("\nDeploying ibackend...", nl=False)
  try:
    click.echo("step 1 out of 2...", nl=False)
    stage = _utils.before_hook(stage)
  except Exception as exception:
    click.echo("\nAn error occured during step 1 of ibackend deployment: %s" % exception.message)
    exit(1)
  try:
    click.echo("\rstep 2 out of 2...", nl=False)
    deploy_backend(stage, "i")
    click.echo("\rIbackend deployed successfully              ")
  except Exception as exception:
    click.echo("\nAn error occured during step 2 of ibackend deployment: %s" % exception.message)
    exit(1)


@cli.command('jbackend')
@click.argument('stage_name')
def jbackend(stage_name):
  """Deploy jbackend <stage>"""
  click.echo("\nDeploying jbackend...", nl=False)
  stage = _get_stage_object(stage_name)
  if not _check_stage_file(stage_name):
    click.echo("\nStage file '%s' not found." % stage)
    exit(1)
  try:
    click.echo("step 1 out of 2...", nl=False)
    stage = _utils.before_hook(stage)
  except Exception as exception:
    click.echo("\nAn error occured during step 1 of jbackend deployment: %s" % exception.message)
    exit(1)
  try:
    click.echo("\rstep 2 out of 2...", nl=False)
    deploy_backend(stage, "j")
    click.echo("\rJbackend deployed successfully              ")
  except Exception as exception:
    click.echo("\nAn error occured during step 2 of jbackend deployment: %s" % exception.message)
    exit(1)


@cli.command('cron')
@click.argument('stage_name')
@click.option('--cron-frequency-minutes', '-m', default=None, show_default=True,
              help='Cron job schedule in minutes')
@click.option('--cron-frequency-hours', '-h', default=None, show_default=True,
              help='Cron job schedule in hours')
def cron(stage_name, cron_frequency_minutes, cron_frequency_hours):
  """Deploy cron file <stage>"""
  if not _check_stage_file(stage_name):
    click.echo("\nStage file '{}' not found.".format(stage_name))
    exit(1)
  stage = _get_stage_object(stage_name)
  click.echo("\nDeploying cron...", nl=False)
  with click.open_file(_constants.CRON_FILE, "w") as cron_file:
    if cron_frequency_minutes is None and cron_frequency_hours is None:
      cron_file.write(_constants.EMPTY_CRON_TEMPLATE)
    else:
      if cron_frequency_minutes and not cron_frequency_hours:
        cron_file.write(_constants.CRON_TEMPLATE
                        .format(str(cron_frequency_minutes),
                                "minutes"))
      elif cron_frequency_hours and not cron_frequency_minutes:
        cron_file.write(_constants.CRON_TEMPLATE
                        .format(str(cron_frequency_hours),
                                "hours"))
      else:
        click.echo("Please choose only one of the two options: -m/-h")
        exit(1)
  try:
    click.echo("step 1 out of 2...", nl=False)
    stage = _utils.before_hook(stage)
  except Exception as exception:
    click.echo("\nAn error occured during step 1 of cron deployment: %s" % exception.message)
    exit(1)
  try:
    click.echo("\rstep 2 out of 2...", nl=False)
    deploy_cron(stage)
    click.echo("\rCron deployed successfully              ")
  except Exception as exception:
    click.echo("\nAn error occured during step 2 of cron deployment: %s" % exception.message)
    exit(1)


@cli.command('migration')
@click.argument('stage_name')
@click.option('-use_service_account', is_flag=True, default=False)
def migration(stage_name, use_service_account):
  """Deploy migration <stage>"""
  click.echo("\nDeploying migration...", nl=False)
  if not _check_stage_file(stage_name):
    click.echo("\nStage file '%s' not found." % stage_name)
    exit(1)
  stage = _get_stage_object(stage_name)
  steps = "4"
  # Step 1
  try:
    click.echo("step 1 out of {}...".format(steps), nl=False)
    stage = _utils.before_hook(stage)
  except Exception as exception:
    click.echo("\nAn error occured during step 1 of migration deployment: {}".format(exception))
    exit(1)
  # Step 2
  try:
    click.echo("\rstep 2 out of {}...".format(steps), nl=False)
    _utils.check_variables()
    migration_subprocess = _utils.before_task(stage, use_service_account)
  except Exception as exception:
    click.echo("\nAn error occured during step 2 of migration deployment: {}".format(exception))
    exit(1)
  # Step 3
  try:
    click.echo("\rstep 3 out of {}...".format(steps), nl=False)
    subprocess.Popen(("flask db upgrade"
                      "flask db_seeds"),
                     cwd="{}/backends".format(stage.workdir),
                     shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
  except Exception as exception:
    click.echo("\nAn error occured during step 3 \
               of migration deployment: {}".format(exception.message))
    exit(1)
  # Step 4 - cleanup
  try:
    click.echo("\rstep 4 out of {}...".format(steps), nl=False)
    os.killpg(os.getpgid(migration_subprocess.pid), signal.SIGTERM)
  except Exception as exception:
    click.echo("\nAn error occured during step 3 \
               of migration deployment: {}".format(exception.message))
    exit(1)
  click.echo("\rMigration deployed successfully              ")


@cli.command('db_seeds')
@click.argument('stage_name')
def db_seeds(stage_name):
  """Add seeds to DB"""
  if not _check_stage_file(stage_name):
    click.echo("\nStage file '%s' not found." % stage_name)
    exit(1)
  stage_file = _get_stage_file(stage_name)
  source_stage_file_and_command_script(stage_file, 'db_seeds')


@cli.command('reset_pipeline')
@click.argument('stage_name')
@click.option('-use_service_account', is_flag=True, default=False)
@click.option('--verbose', '-v', is_flag=True, default=False)
def reset_pipeline(verbose, stage_name, use_service_account):
  """Reset Job statuses in Pipeline"""
  click.echo("\nReseting pipeline...", nl=False)
  if not _check_stage_file(stage_name):
    click.echo("\nStage file '%s' not found." % stage_name)
    exit(1)
  stage = _get_stage_object(stage_name)
  steps = 4
  try:
    click.echo("step 1 out of {}...".format(steps), nl=False)
    stage = _utils.before_hook(stage)
  except Exception as exception:
    click.echo("\nAn error occured during step 1 of reseting pipeline: {}"
               .format(exception.message))
    exit(1)
  try:
    click.echo("\rstep 2 out of {}...".format(steps), nl=False)
    _utils.check_variables()
    before_task_subprocess = _utils.before_task(stage, use_service_account)
  except Exception as exception:
    click.echo("\nAn error occured during step 2 of reseting pipeline: {}"
               .format(exception.message))
    exit(1)
  try:
    click.echo("\rstep 3 out of {}...".format(steps), nl=False)
    backends_dir = os.path.join(stage.workdir, "backends/")
    task_path = os.path.join(_constants.TASKS_PATH, _constants.RESET_PIPELINE_TASK)
    from shutil import copy
    copy(task_path, backends_dir)

    subprocess.Popen("python {}".format(task_path),
                     cwd=backends_dir,
                     shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
  except Exception as exception:
    click.echo("\nAn error occured during step 3 of reseting pipeline: {}"
               .format(exception.message))
    exit(1)
  # Step 4 - cleanup
  try:
    click.echo("\rstep 4 out of {}...".format(steps), nl=False)
    os.killpg(os.getpgid(before_task_subprocess.pid), signal.SIGTERM)
  except Exception as exception:
    click.echo("\nAn error occured during step 4 of reseting pipeline: {}"
               .format(exception.message))
    exit(1)
  click.echo("\rReset pipeline succeeded               ")


if __name__ == '__main__':
  cli()
