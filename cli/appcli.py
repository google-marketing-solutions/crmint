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
import sys

PLUGIN_FOLDER = os.path.join(os.path.dirname(__file__), 'crmint_commands')
CLI_DIR = os.path.dirname(__file__)
sys.path.insert(0, CLI_DIR)

import click
from crmint_commands.utils import shared


class CRMintCLI(click.MultiCommand):
  """App multi command CLI"""

  def __init__(self, *args, **kwargs):
    click.MultiCommand.__init__(self, *args, **kwargs)

  def list_commands(self, ctx):
    rv = []
    for filename in os.listdir(PLUGIN_FOLDER):
      if not filename.startswith("_") and filename.endswith(".py"):
        rv.append(filename[:-3])
    rv.sort()
    return rv

  def get_command(self, ctx, name):
    ns = {}
    full_name = os.path.join(PLUGIN_FOLDER, "%s%s" % (name, ".py"))
    with open(full_name) as f:
      code = compile(f.read(), full_name, 'exec')
      eval(code, ns, ns)
    return ns.get('cli', None)


CLI = CRMintCLI(help='Manage your CRMint instances on GCP or locally.')


def entry_point():
  shared.check_variables()
  CLI()
