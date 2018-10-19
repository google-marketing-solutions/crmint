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

import click
from crmint_commands.utils import constants
from crmint_commands.utils import database
from crmint_commands.utils import shared
import os
import subprocess


@click.group()
def cli():
  """CRMint Local Dev CLI"""
  pass

####################### SETUP #######################

CONFIG_FILES = [
    ("backends/instance/config.py.example", "backends/instance/config.py"),
    ("backends/gae_dev_ibackend.yaml.example", "backends/gae_dev_ibackend.yaml"),
    ("backends/gae_dev_jbackend.yaml.example", "backends/gae_dev_jbackend.yaml"),
    ("backends/data/app.json.example", "backends/data/app.json"),
    ("backends/data/service-account.json.example", "backends/data/service-account.json")
]


def _create_config_file(example_path, dest):
  if not os.path.exists(dest):
    copyfile(example_path, dest)


def _create_all_configs():
  for config in CONFIG_FILES:
    full_src_path = os.path.join(constants.PROJECT_DIR, config[0])
    full_dest_path = os.path.join(constants.PROJECT_DIR, config[1])
    _create_config_file(full_src_path, full_dest_path)



@cli.command('setup')
def setup():
  """Setup DB and config files required for local development."""  
  click.echo("Setup in progress...")
  try:
    components = [database.create_database, _create_all_configs,
                  shared.install_requirements]
    with click.progressbar(components) as progress_bar:
      for component in progress_bar:
        component()
  except Exception as exception:
    click.echo("Setup failed: {}".format(exception))
    exit(1)


####################### RUN #######################


@cli.command('run')
@click.argument('component')
def run(component):
  """Run backend or frontend services\n
  COMPONENT: frontend/backend
  """
  # TODO
  pass


@cli.group()
def do():
  """Do local development tasks."""
  pass


@do.command('requirements')
def do_requirements():
  """Install required Python packages."""
  # TODO
  pass


@do.command('add_migration')
def do_add_migration():
  """Create a new DB migration."""
  # TODO
  pass


@do.command('migrations')
def do_migrations():
  """Run new DB migrations."""
  # TODO
  pass


@do.command('seeds')
def do_seeds():
  """Run DB seeds script."""
  # TODO
  pass


@do.command('reset')
def do_reset():
  """Reset jobs and pipelines to status 'idle'"""
  # TODO
  pass


@cli.command('console')
def console():
  """Run shell console for backend."""
  # TODO
  pass

@cli.command('dbconsole')
def dbconsole():
  """Run DB console for development environment."""
  # TODO
  pass
