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

import importlib
import json
import os
import sys

import click

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
CLI_DIR = os.path.join(PROJECT_DIR, 'cli')
PLUGIN_FOLDER = os.path.join(CLI_DIR, 'commands')
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, CLI_DIR)

from backend.common import insight  # pylint: disable=g-import-not-at-top
from cli.utils import shared

SEPARATOR = '='*74


def _set_insight_opt_out(config, value):
  config['opt_out'] = value
  with open(insight.INSIGHT_CONF_FILEPATH, 'w+') as fp:
    json.dump(config, fp)


def print_version(ctx, param, value):
  del param  # Unused parameter.
  if not value or ctx.resilient_parsing:
    return
  click.echo(insight.get_crmint_version())
  ctx.exit()


class CRMintCLI(click.MultiCommand):
  """App multi commands CLI."""

  def _ask_permission(self):
    pkg_name = 'CRMint'
    msg = click.style(SEPARATOR, fg='black')
    msg += click.style(
        '\nWe\'re constantly looking for ways to make ',
        fg='yellow')
    msg += click.style(pkg_name, fg='red', bold=True)
    msg += click.style(
        ' better! \nMay we anonymously report usage statistics to improve the'
        'tool over time? \nMore info: https://github.com/google/crmint & '
        'https://google.github.io/crmint',
        fg='yellow')
    msg += click.style(f'\n{SEPARATOR}', fg='black')
    if click.confirm(msg, default=True):
      return True
    return False

  def list_commands(self, ctx):
    rv = []
    for filename in os.listdir(PLUGIN_FOLDER):
      matching_conditions = [
          not filename.startswith('_'),
          not filename.endswith('_tests.py'),
          filename.endswith('.py'),
      ]
      if all(matching_conditions):
        rv.append(filename[:-3])
    rv.sort()
    return rv

  def get_command(self, ctx, name):
    command_path = os.path.join(PLUGIN_FOLDER, f'{name}.py')
    spec = importlib.util.spec_from_file_location('loaded_cmd', command_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, 'cli', None)

  def resolve_command(self, ctx, args):
    tracker = insight.GAProvider(allow_new_client_id=True)
    if '--no-insight' in args:
      args.remove('--no-insight')
      _set_insight_opt_out(tracker.config, True)
    if tracker.opt_out is None:
      # None means that we still didn't record the user consent.
      tracker.track('downloaded')
      permission_given = self._ask_permission()
      _set_insight_opt_out(tracker.config, not permission_given)
      # Reload with the new configuration.
      tracker = insight.GAProvider()
      tracker.track('installed')
    tracker.track(*args)
    return super().resolve_command(ctx, args)


@click.command(
    cls=CRMintCLI, help='Manage your CRMint instances on GCP or locally.')
@click.option(
    '--version',
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help='Print out CRMint version.')
def cli() -> None:
  """Root command."""


def entry_point():
  shared.check_variables()
  cli()
