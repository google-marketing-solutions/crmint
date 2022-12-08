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
@click.option('--use_vpc', is_flag=True, default=False,
              help='[Deprecated] Deploys a Virtual Private Cloud network')
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def install(ctx: click.Context, use_vpc: bool, debug: bool) -> None:
  """Runs all commands needed to deploy CRMint in one command."""
  del use_vpc
  ctx.invoke(stages.create, debug=debug)
  ctx.invoke(cloud.checklist, debug=debug)
  ctx.invoke(cloud.setup, debug=debug)
  ctx.invoke(cloud.migrate, debug=debug)


@cli.command('update')
@click.option('--version', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def update(ctx: click.Context, version: str, debug: bool):
  """Updates CRMint to its latest stable version and Setup."""
  ctx.invoke(stages.update, version=version, debug=debug)
  ctx.invoke(cloud.setup, debug=debug)
  ctx.invoke(cloud.migrate, debug=debug)


@cli.command('allow-users')
@click.argument('user_emails', type=str)
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def allow_users(ctx: click.Context, user_emails: str, debug: bool):
  """Allow a list of user emails to access CRMint and Setup."""
  ctx.invoke(stages.allow_users, user_emails=user_emails, debug=debug)
  ctx.invoke(cloud.setup, debug=debug)


if __name__ == '__main__':
  cli()
