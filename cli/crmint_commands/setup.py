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
import subprocess
import click
from crmint_commands.utils import shared


def is_executable_file(path):
  return os.path.isfile(path) and os.access(path, os.X_OK)


def is_not_empty(result):
  return bool(result)


def install_component(component_name, check_command, install_command, check_function):
  try:
    click.echo("\nChecking {}...           ".format(component_name), nl=False)
    cmd_process = subprocess.Popen(check_command,
                                   shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    result = cmd_process.communicate()[0].strip()
    if not check_function(result):
      click.echo("\rInstalling {}...          ".format(component_name))

      res = subprocess.Popen(install_command,
                             shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
      err = res.communicate()[1]
      if err:
        # TODO print to log file / verbose option
        click.echo("[w] Error when installing {}. Check logs for details".format(component_name))
    else:
      click.echo("")
  except:
    raise Exception("{} installation failed".format(component_name))


@click.command()
def cli():
  """Prepare the environment before deployment"""
  click.echo("Setup in progress...")
  try:
    gcloud_install_command = """
    export CLOUDSDK_CORE_DISABLE_PROMPTS=1
    export CLOUDSDK_INSTALL_DIR=`realpath \"$gcloud_sdk_dir/..\"
    curl https://sdk.cloud.google.com | bash
    """

    components = [
        ("Homebrew",
         "command -v brew",
         "echo Please execute the following command first:\n\'/usr/bin/ruby " +
         "-e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\"\'",
         is_executable_file),
        ("Node.js",
         "command -v node",
         "brew install node",
         is_executable_file),
        ("Angular",
         "command -v ng",
         "npm install -g @angular/cli",
         is_executable_file),
        ("MySQL",
         "command -v mysql",
         "brew install mysql",
         is_executable_file),
        ("Google Cloud SDK",
         "command -v $gcloud_sdk_dir/bin/gcloud",
         gcloud_install_command,
         is_executable_file),
        ("gcloud component app-engine-python",
         "$gcloud_sdk_dir/bin/gcloud --version | grep \"app-engine-python\"",
         "$gcloud_sdk_dir/bin/gcloud components install app-engine-python",
         is_not_empty
        ),
        shared.check_variables
        ]
    with click.progressbar(components) as progress_bar:
      for component in progress_bar:
        if isinstance(component, tuple):
          install_component(component[0], component[1], component[2], component[3])
        else:
          component()
  except Exception as exception:
    click.echo("Setup failed: {}".format(exception))
    exit(1)
