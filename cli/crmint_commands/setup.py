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
from crmint_commands.utils import constants
from crmint_commands.utils import database


def brew_check():
  try:
    result = subprocess.Popen("$(command -v brew)",
                     shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE).communicate()[0]
    if not result:
      click.echo("\rInstalling brew...", nl=False)
      brew = "sudo -S /usr/bin/ruby -e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\""
      subprocess.Popen(brew,
                     shell=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
  except:
    raise Exception("Brew installation failed")



@click.command()
def cli():
  """Prepare local machine to work"""
  click.echo("Setup in progress...")
  try:
    components = [brew_check]
    with click.progressbar(components) as progress_bar:
      for component in progress_bar:
        component()
  except Exception as exception:
    click.echo("Setup failed: {}".format(exception))
    exit(1)
