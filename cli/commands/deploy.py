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

import os
import click
import commands._constants
import commands._utils
import stage_variables
import sys


def _get_stage_file(stage):
  stage_file = "{}/{}.py".format(commands._constants.STAGE_DIR, stage)
  return stage_file


def _check_stage_file(stage):
  stage_file = _get_stage_file(stage)
  if not os.path.isfile(stage_file):
      click.echo("\nStage file '%s' not found." % stage)
      exit(1)


def source_stage_file_and_command_script(stage_file, command):
  os.system("""SCRIPTS_DIR="{}"
        source \"{}\"
        source \"{}/deploy/before_hook.sh\"
        source \"{}/deploy/{}.sh\""""
            .format(commands._constants.SCRIPTS_DIR, stage_file,
                    commands._constants.SCRIPTS_DIR,
                    commands._constants.SCRIPTS_DIR, command))


def deploy_frontend(stage_name):
  click.echo("\nDeploying frontend...")
  stage = getattr(__import__("stage_variables.%s" % stage_name), stage_name)
  try:
    click.echo("Step 1 out of 2...")
    commands._utils.before_hook(stage)
    click.echo("Step 2 out of 2...")
    click.echo("Frontend deployed successfully!")
  except Exception as e:
    click.echo("\nAn error occured. Details: %s" % e.message)


@click.group()
def cli():
  """CRMint Deploy application to Google App Engine"""
  pass


@cli.command('all')
@click.argument('stage')
@click.pass_context
def deploy_all(context, stage):
  """Deploy all <stage>"""
  deploy_components = [frontend]
  # , ibackend, jbackend, cron, migration]
  with click.progressbar(deploy_components) as bar:
    for component in bar:
      context.invoke(component, stage=stage)


@cli.command('frontend')
@click.argument('stage')
def frontend(stage):
  """Deploy frontend <stage>"""
  _check_stage_file(stage)
  deploy_frontend(stage)

@cli.command('ibackend')
@click.argument('stage')
def ibackend(stage):
  """Deploy ibackend <stage>"""
  stage_file = _get_stage_file(stage)
  _check_stage_file(stage_file)
  source_stage_file_and_command_script(stage_file, 'ibackend')


@cli.command('jbackend')
@click.argument('stage')
def jbackend(stage):
  """Deploy jbackend <stage>"""
  _check_stage_file(stage)
  source_stage_file_and_command_script(stage_file, 'jbackend')


@cli.command('migration')
@click.argument('stage')
def migration(stage):
  """Deploy migration <stage>"""
  _check_stage_file(stage)
  source_stage_file_and_command_script(stage_file, 'migration')


# [TODO] Make cm and ch options mutual exclusiv
@cli.command('cron')
@click.argument('stage')
@click.option('--cron-frequency-minutes', '-m', default=None, show_default=True,
              help='Cron job schedule in minutes')
@click.option('--cron-frequency-hours', '-h', default=None, show_default=True,
              help='Cron job schedule in hours')
def cron(stage, cron_frequency_minutes, cron_frequency_hours):
  """Deploy cron file <stage>"""
  _check_stage_file(stage)
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
@click.argument('stage')
def db_seeds(stage):
  """Add seeds to DB"""
  _check_stage_file(stage)
  source_stage_file_and_command_script(stage_file, 'db_seeds')


@cli.command('reset_pipeline')
@click.argument('stage')
def reset_pipeline(stage):
  """Reset Job statuses in Pipeline"""
  stage_file = _get_stage_file(stage)
  _check_stage_file(stage_file)
  source_stage_file_and_command_script(stage_file, 'reset_pipeline')


if __name__ == '__main__':
  cli()
