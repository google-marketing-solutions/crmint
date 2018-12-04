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

PLUGIN_FOLDER = os.path.join(os.path.dirname(__file__), 'commands')
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
CLI_DIR = os.path.dirname(__file__)
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, CLI_DIR)

import click
from cli.utils import shared
from backends.core import insight


class CRMintCLI(click.MultiCommand):
  """App multi command CLI"""

  def __init__(self, *args, **kwargs):
    super(CRMintCLI, self).__init__(*args, **kwargs)
    self.insight = insight.GATracker()
    self.insight.track('downloaded')
    if self.insight.opt_out is None:
      # None means that we still didn't record the user consent.
      permission_given = self._ask_permission()
      self.insight.set_opt_out(not permission_given)

  def _ask_permission(self):
    pkg_name = "CRMint"
    msg = click.style(
        "==========================================================================",
        fg="black")
    msg += click.style(
        "\nWe're constantly looking for ways to make ",
        fg='yellow')
    msg += click.style(pkg_name, fg="red", bold=True)
    msg += click.style(
        " better! \nMay we anonymously report usage statistics to improve the tool over time? \n"
        "More info: https://github.com/google/crmint & https://google.github.io/crmint",
        fg='yellow')
    msg += click.style(
        "\n==========================================================================",
        fg='black')
    if click.confirm(msg, default=True):
      return True
    return False

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

  def resolve_command(self, ctx, args):
    self.insight.track(*args)
    return super(CRMintCLI, self).resolve_command(ctx, args)


CLI = CRMintCLI(help='Manage your CRMint instances on GCP or locally.')


def entry_point():
  shared.check_variables()
  CLI()
