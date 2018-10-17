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
"""Setup command"""

import os.path
from shutil import copyfile
import subprocess
import click
from crmint_commands import _constants


DATABASE_NAME = "crmintapp"
DATABASE_USER = "crmintapp"


CONFIG_FILES = [
    ("backends/instance/config.py.example", "backends/instance/config.py"),
    ("backends/gae_dev_ibackend.yaml.example", "backends/gae_dev_ibackend.yaml"),
    ("backends/gae_dev_jbackend.yaml.example", "backends/gae_dev_jbackend.yaml"),
    ("backends/data/app.json.example", "backends/data/app.json"),
    ("backends/data/service-account.json.example", "backends/data/service-account.json")
]


REQUIREMENTS_DIR = os.path.join(_constants.PROJECT_DIR, "cli/requirements.txt")
LIB_DEV_PATH = os.path.join(_constants.PROJECT_DIR, "backends/lib_dev")


def _create_database():
  db_setup = subprocess.Popen("mysqlshow -u{} -p{} 2>/dev/null | grep {};"
                              .format(DATABASE_NAME, DATABASE_USER, DATABASE_NAME),
                              stdout=subprocess.PIPE,
                              shell=True)
  if not db_setup.stdout.read():
    db_command = """sudo service mysql start | sudo -S mysql << EOF
CREATE DATABASE {} CHARACTER SET utf8;
GRANT ALL PRIVILEGES ON {}.* TO '{}'@'localhost' IDENTIFIED BY '{}';
FLUSH PRIVILEGES;
quit
EOF | service mysql stop
"""
    res = subprocess.Popen(db_command.format(DATABASE_NAME,
                                             DATABASE_USER, DATABASE_USER, DATABASE_USER),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           shell=True)
    error_message = res.communicate()[1]
    if error_message:
      raise Exception(error_message)


def _create_config_file(example_path, dest):
  if not os.path.exists(dest):
    print dest
    copyfile(example_path, dest)


def _create_all_configs():
  for config in CONFIG_FILES:
    full_src_path = os.path.join(_constants.PROJECT_DIR, config[0])
    full_dest_path = os.path.join(_constants.PROJECT_DIR, config[1])
    _create_config_file(full_src_path, full_dest_path)


def _pip_install():
  try:
    subprocess.Popen("pip install -r {} -t {}".format(REQUIREMENTS_DIR, LIB_DEV_PATH),
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     shell=True)
  except:
    raise Exception("Requirements could not be installed")

@click.command()
def cli():
  """Prepare local machine to work"""
  click.echo("Setup in progress...")
  try:
    components = [_create_database, _create_all_configs, _pip_install]
    with click.progressbar(components) as progress_bar:
      for component in progress_bar:
        component()
  except Exception as exception:
    click.echo("Setup failed: {}".format(exception))
    exit(1)
