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
import constants

def _get_stage_file(stage):
  stage_file = "{}/{}.sh".format(constants.STAGE_DIR, stage)
  return stage_file

def _check_stage_file(stage_file):
  if not os.path.isfile(stage_file):
      click.echo("Stage file not found.")
      exit(1)

def source_stage_file_and_command_script(stage_file, command):
  os.system("""SCRIPTS_DIR="{}"
        source \"{}\"
        source \"{}/deploy/before_hook.sh\"
        source \"{}/deploy/{}.sh\""""
          .format(constants.SCRIPTS_DIR,stage_file, constants.SCRIPTS_DIR,
                  constants.SCRIPTS_DIR, command))

@click.group()
def cli():
  """CRMint Deploy"""
  pass

@cli.command('all')
@click.argument('stage')
@click.pass_context
def all(context, stage):
  """Deploy all <stage>"""
  context.invoke(frontend, stage=stage)
  context.invoke(ibackend, stage=stage)
  context.invoke(jbackend, stage=stage)
  context.invoke(cron, stage=stage)
  context.invoke(migration, stage=stage)

@cli.command('frontend')
@click.argument('stage')
def frontend(stage):
  """Deploy frontend <stage>"""
  stage_file = _get_stage_file(stage)
  _check_stage_file(stage_file)
  source_stage_file_and_command_script(stage_file, 'frontend')

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
  stage_file = _get_stage_file(stage)
  _check_stage_file(stage_file)
  source_stage_file_and_command_script(stage_file, 'jbackend')

@cli.command('migration')
@click.argument('stage')
def migration(stage):
  """Deploy migration <stage>"""
  stage_file = _get_stage_file(stage)
  _check_stage_file(stage_file)
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
  stage_file = _get_stage_file(stage)
  _check_stage_file(stage_file)
  with open(constants.CRON_FILE, "w") as cron_file:
      if cron_frequency_minutes is None and cron_frequency_hours is None:
          cron_file.write(constants.EMPTY_CRON_TEMPLATE)
      else:
          if cron_frequency_minutes:
              cron_file.write(constants.CRON_TEMPLATE
                              .format(str(cron_frequency_minutes),
                                      "minutes"))
          if cron_frequency_hours:
              cron_file.write(constants.CRON_TEMPLATE
                              .format(str(cron_frequency_hours),
                                      "hours"))
  source_stage_file_and_command_script(stage_file, 'cron')

@cli.command('db_seeds')
@click.argument('stage')
def db_seeds(stage):
  """Add seeds to DB"""
  stage_file = _get_stage_file(stage)
  _check_stage_file(stage_file)
  source_stage_file_and_command_script(stage_file, 'db_seeds')

@cli.command('reset_pipeline')
@click.argument('stage')
def reset_pipeline(stage):
  """Reset Job statuses in Pipeline"""
  pass

if __name__ == '__main__':
  cli()
