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
import subprocess

import click

from cli.utils import constants
from cli.utils import database
from cli.utils import shared


def is_executable_file(path):
  return os.path.isfile(path) and os.access(path, os.X_OK)


def is_not_empty(result):
  return bool(result)


@click.group()
def cli():
  """Local development utilities"""
  pass


####################### SETUP #######################


@click.command('setup')
def setup():
  """Prepare the environment before deployment."""
  click.echo(click.style(">>>> Setup local env", fg='magenta', bold=True))
  components = [
      (
          "Homebrew",
          "command -v brew",
          "echo Please execute the following command first:\n\'/usr/bin/ruby " +
          "-e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\"\'",
          is_executable_file
      ),
      (
          "Node.js",
          "command -v node",
          "brew install node",
          is_executable_file
      ),
      (
          "Angular",
          "command -v ng",
          "npm install -g @angular/cli",
          is_executable_file
      ),
      (
          "MySQL",
          "command -v mysql",
          "brew install mysql",
          is_executable_file
      ),
      (
          "Google Cloud SDK",
          "command -v gcloud",
          "export CLOUDSDK_CORE_DISABLE_PROMPTS=1 && \
           curl https://sdk.cloud.google.com | bash",
          is_executable_file
      ),
      (
          "App Engine Python",
          "gcloud --version | grep \"app-engine-python\"",
          "gcloud components install app-engine-python",
          is_not_empty
      ),
  ]
  for component in components:
    step_name, check_cmd, install_cmd, check_cmd_res_func = component
    status, out, err = shared.execute_command("Check %s" % step_name, check_cmd)
    if status == 0 and check_cmd_res_func(out.strip()):
      click.echo("     Already installed.")
    else:
      shared.execute_command("Install %s" % step_name, install_cmd)
  click.echo(click.style("Done.", fg='magenta', bold=True))



@cli.command('init')
def init():
  """Initialize the database for local development."""
  click.echo(click.style(">>>> Initialization", fg='magenta', bold=True))
  params = dict(
      db_name=database.DATABASE_NAME,
      db_user=database.DATABASE_USER,
      db_pass=database.DATABASE_PASSWORD
  )
  components = [
      (
          "Create database",
          "echo \"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8;\" | mysql -h 127.0.0.1 -u root -proot".format(**params),
      ),
      (
          "Grant privileges to {db_user}".format(**params),
          "echo \"GRANT ALL PRIVILEGES ON {db_user}.* TO '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}';\" | mysql -h 127.0.0.1 -u root -proot".format(**params),
      ),
      (
          "Cleaning",
          "echo \"FLUSH PRIVILEGES;\" | mysql -h 127.0.0.1 -u root -proot".format(**params),
      ),
      (
          "Create local service account file from a template",
          "cp backends/data/service-account.json.example backends/data/service-account.json",
      )
  ]
  for component in components:
    name, cmd = component
    shared.execute_command(name, cmd, cwd=constants.PROJECT_DIR)
  click.echo(click.style("Done.", fg='magenta', bold=True))


####################### DO ########################


@cli.group()
def do():
  """Do local development tasks."""
  pass


@do.command('requirements')
@click.option('--debug/--no-debug', default=False)
def do_requirements(debug):
  """Install required Python packages."""
  click.echo(click.style(">>>> Install requirements", fg='magenta', bold=True))
  components = [
      (
          "Install interface backend requirements",
          "pip install -r ibackend/requirements.txt -t lib",
      ),
      (
          "Install jobs backend requirements",
          "pip install -r jbackend/requirements.txt -t lib",
      ),
      (
          "Install documentation requirements",
          "pip install \"sphinx==1.7.2\" \"sphinx-autobuild==0.7.1\"",
      )
  ]
  for component in components:
    name, cmd = component
    shared.execute_command(name, cmd,
        cwd=constants.BACKENDS_DIR,
        debug=debug)
  click.echo(click.style("Done.", fg='magenta', bold=True))


@do.command('add_migration')
@click.option('--args')
@click.option('--debug/--no-debug', default=True)
def do_add_migration(args, debug):
  """Create a new DB migration."""
  if not args:
    args = ""
  click.echo(click.style(">>>> Add Migration", fg='magenta', bold=True))
  os.environ["PYTHONPATH"] = "{google_sdk_dir}/platform/google_appengine:lib".format(
      google_sdk_dir=os.environ["GOOGLE_CLOUD_SDK"])
  os.environ['FLASK_APP'] = "run_ibackend.py"
  os.environ['FLASK_DEBUG'] = "1"
  os.environ['GAE_APPLICATION'] = ""
  components = [
      (
          "Create new migration (if needed)",
          "python -m flask db revision %s" % args,
      ),
  ]
  for component in components:
    name, cmd = component
    shared.execute_command(name, cmd,
        cwd=constants.BACKENDS_DIR,
        debug=debug)
  click.echo(click.style("Done.", fg='magenta', bold=True))


@do.command('migrations')
@click.option('--debug/--no-debug', default=False)
def do_migrations(debug):
  """Run new DB migrations."""
  click.echo(click.style(">>>> Run Migrations", fg='magenta', bold=True))
  os.environ["PYTHONPATH"] = "{google_sdk_dir}/platform/google_appengine:lib".format(
      google_sdk_dir=os.environ["GOOGLE_CLOUD_SDK"])
  os.environ['FLASK_APP'] = "run_ibackend.py"
  os.environ['FLASK_DEBUG'] = "1"
  os.environ['GAE_APPLICATION'] = ""
  components = [
      (
          "Run the db upgrade",
          "python -m flask db upgrade",
      ),
  ]
  for component in components:
    name, cmd = component
    shared.execute_command(name, cmd,
        cwd=constants.BACKENDS_DIR,
        debug=debug)
  click.echo(click.style("Done.", fg='magenta', bold=True))
