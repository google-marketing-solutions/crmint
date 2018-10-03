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

@click.group()
def cli():
  """Deploy cli"""
  pass

# [TODO] Make cm and ch options mutual exclusiv
@cli.command('cron')
@click.argument('stage')
@click.option('--cron-frequency-minutes', '-cm', default=None, show_default=True,
              help='Cron job schedule in minutes')
@click.option('--cron-frequency-hours', '-ch', default=None, show_default=True,
              help='Cron job schedule in hours')
def cron(stage, cron_frequency_minutes, cron_frequency_hours):
  """Deploy only the cron file for a STAGE"""
  stage_file = _get_stage_file(stage)
  if not os.path.isfile(stage_file):
      click.echo("Stage file not found.")
      exit(1)
  else:
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
      os.system("""source \"{}\"
              source \"{}/deploy/before_hook.sh\"
              source \"{}/deploy/cron.sh\""""
                .format(stage_file, constants.SCRIPTS_DIR,
                        constants.SCRIPTS_DIR))

if __name__ == '__main__':
  cli()
