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

"""Command line combining multiple CRMint commands into one."""

import click

from cli.commands import cloud
from cli.commands import stages


@click.group()
def cli():
  """Deploys CRMint in one command."""


@cli.command('install')
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def install(ctx: click.Context, debug: bool) -> None:
  """Runs all commands needed to deploy CRMint in one command."""
  ctx.invoke(stages.create, debug=debug)
  ctx.invoke(stages.migrate, debug=debug)
  ctx.invoke(cloud.checklist, debug=debug)
  ctx.invoke(cloud.setup, debug=debug)
  ctx.invoke(cloud.deploy, debug=debug)


if __name__ == '__main__':
  cli()
