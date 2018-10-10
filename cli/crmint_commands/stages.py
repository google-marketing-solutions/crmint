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
from crmint_commands import _constants


@click.group()
def cli():
  """CRMint manage stages"""
  pass


# TODO rename cli_setup to replace the current setup once the migration is done
@cli.command('setup')
@click.argument('stage')
def setup(stage):
  """Setup a new stage"""
  if "%s.sh" % stage in os.listdir(_constants.STAGE_DIR):
    click.echo("Stage {} already exists".format(stage))
    return
  os.system("""STAGE_NAME={}
            SCRIPTS_DIR={}
            source "{}/stages/setup_cli.sh" """
            .format(stage, _constants.SCRIPTS_DIR, _constants.SCRIPTS_DIR))


@cli.command('check')
@click.argument('stage')
def check(stage):
  """Check stage"""
  if "%s.sh" % stage not in os.listdir(_constants.STAGE_DIR):
    click.echo("Stage not found")
    return
  os.system("""stage={}
            SCRIPTS_DIR={}
            source "{}/stages/check_cli.sh" """
            .format(stage, _constants.SCRIPTS_DIR,
                    _constants.SCRIPTS_DIR))


@cli.command('create')
@click.argument('stage')
def create(stage):
  """Create new project in Google Cloud and add instances"""
  os.system("""STAGE_NAME={}
    source "{}/stages/create.sh" """.format(stage, _constants.SCRIPTS_DIR))


def _ignore_stage_file(file_name):
  IGNORED_STAGE_FILES = ["__init__.py"]
  ENDS_WITH = [".pyc", ".example"]
  return file_name in IGNORED_STAGE_FILES or file_name.endswith(tuple(ENDS_WITH))

@cli.command('list')
def list_stages():
  """List your stages defined in scripts/variables/stages directory"""
  for file_name in os.listdir(_constants.STAGE_DIR):
    if not _ignore_stage_file(file_name):
      click.echo(file_name[:-3])
