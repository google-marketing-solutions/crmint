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

"""Command line to setup and deploy CRMint on GCP."""

import collections
import json
import pathlib
import re
import sys
import textwrap
from typing import Union

import click

from cli.utils import insight
from cli.utils import shared
from cli.utils.constants import GCLOUD

_INDENT_PREFIX = '     '


def retrieve_user_roles(user_email: str,
                        stage: shared.StageContext,
                        debug: bool = False) -> list[str]:
  """Returns the list of roles for the given user.

  Args:
    user_email: Email address to check the owner role on.
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  project_id = stage.project_id
  cmd = textwrap.dedent(f"""\
      {GCLOUD} projects get-iam-policy {project_id} \\
          --flatten="bindings[].members" \\
          --filter="bindings.members=user:{user_email}" \\
          --format="value(bindings.role)"
      """)
  _, out, _ = shared.execute_command(
      'Retrieve user IAM roles',
      cmd,
      debug=debug,
      debug_uses_std_out=False)
  return out.strip().split('\n')


def check_billing_configured(stage: shared.StageContext,
                             debug: bool = False) -> bool:
  """Returns True if billing is configured for the given project.

  Args:
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  project_id = stage.project_id
  cmd = textwrap.dedent(f"""\
      {GCLOUD} beta billing projects describe {project_id} \\
          --format="value(billingAccountName)"
      """)
  _, out, _ = shared.execute_command(
      'Retrieve billing account name',
      cmd,
      debug=debug,
      debug_uses_std_out=False)
  # If not configured, Google Cloud documentation states that it will be empty.
  return bool(out.strip())


def check_billing_enabled(stage: shared.StageContext,
                          debug: bool = False) -> bool:
  """Returns True if billing is enabled for the given project.

  Args:
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  project_id = stage.project_id
  cmd = textwrap.dedent(f"""\
      {GCLOUD} beta billing projects describe {project_id} \\
          --format="value(billingEnabled)"
      """)
  _, out, _ = shared.execute_command(
      'Check that billing is enabled',
      cmd,
      debug=debug,
      debug_uses_std_out=False)
  return out.strip().lower() == 'true'


def terraform_switch_workspace(stage: shared.StageContext,
                               debug: bool = False) -> bool:
  """Creates or reuses the workspace that stores the Terraform state.

  Args:
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  cmd = 'terraform workspace list'
  _, out, _ = shared.execute_command(
      'List Terraform workspaces',
      cmd,
      cwd='./terraform',
      debug=debug,
      debug_uses_std_out=False)
  workspaces = [name.lstrip('*').strip() for name in out.strip().split('\n')]
  if stage.project_id not in workspaces:
    cmd = f'terraform workspace new {stage.project_id}'
    shared.execute_command(
        f'Create new Terraform workspace: {stage.project_id}',
        cmd,
        cwd='./terraform',
        debug=debug)
  else:
    cmd = f'terraform workspace select {stage.project_id}'
    shared.execute_command(
        f'Select existing Terraform workspace: {stage.project_id}',
        cmd,
        cwd='./terraform',
        debug=debug)


def patch_etc_hosts(debug: bool = False) -> None:
  """Workaround to avoid Terraform to use IPv6 addresses."""
  cmd = 'bash scripts/force_ipv4_addresses.sh'
  shared.execute_command(
      'Patch /etc/hosts to force IPv4', cmd, cwd='./cli', debug=debug)


def unpatch_etc_hosts(debug: bool = False) -> None:
  """Restores the `/etc/hosts` file."""
  cmd = 'cp /etc/hosts.backup /etc/hosts'
  shared.execute_command(
      'Restore /etc/hosts', cmd, cwd='./cli', debug=debug)


def terraform_init(debug: bool = False) -> bool:
  """Runs the Terraform init command."""
  cmd = 'terraform init -upgrade'
  shared.execute_command(
      'Initialize Terraform', cmd, cwd='./terraform', debug=debug)


def terraform_plan(stage: shared.StageContext, debug: bool = False) -> bool:
  """Runs the Terraform plan command.

  Args:
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  tracker = insight.GAProvider()
  report_usage_id = tracker.client_id if not tracker.opt_out else ''
  cmd = textwrap.dedent(f"""\
      terraform plan \\
          -var-file={stage.stage_path} \\
          -var frontend_image={stage.frontend_image_with_digest} \\
          -var controller_image={stage.controller_image_with_digest} \\
          -var jobs_image={stage.jobs_image_with_digest} \\
          -var report_usage_id={report_usage_id} \\
          -out=/tmp/tfplan
      """)
  shared.execute_command(
      'Generate Terraform plan', cmd, cwd='./terraform', debug=debug)


def terraform_apply(debug: bool = False) -> bool:
  """Runs the Terraform apply command."""
  # NB: No need to set `-var-file` when applying a saved plan.
  cmd = 'terraform apply -auto-approve /tmp/tfplan'
  shared.execute_command(
      'Apply Terraform plan (~10min)', cmd, cwd='./terraform', debug=debug)


def terraform_show_plan(debug: bool = False) -> str:
  """Returns the terraform plan output in a JSON format.

  Args:
    debug: Boolean to force a more verbose output.
  """
  cmd = 'terraform show -json /tmp/tfplan'
  _, out, _ = shared.execute_command(
      'Summarize Terraform plan',
      cmd,
      cwd='./terraform',
      debug=debug,
      debug_uses_std_out=False)
  return out


def configuration_summary_from_plan(debug: bool = False) -> bool:
  """Parses the Terraform plan and outputs a summary."""
  out = terraform_show_plan(debug=debug)
  plan = json.loads(out)
  resources_map = collections.defaultdict(list)
  for resource in plan['configuration']['root_module']['resources']:
    # Check if there is a count condition
    will_be_deployed = True
    count_refs = resource.get('count_expression', {}).get('references', [])
    for ref in count_refs:
      if ref.startswith('var.'):
        varname = ref.removeprefix('var.')
        if varname not in plan['variables']:
          raise ValueError(f'Variable not found for name: {varname}')
        if not plan['variables'][varname]['value']:
          will_be_deployed = False
          break
      else:
        raise ValueError(f'Unsupported count ref: {ref}')
    if will_be_deployed:
      resources_map[resource['type']].append(resource['name'])
  # Print a summary of the configuration
  for resource_type, resource_names in resources_map.items():
    resource_type_cleaned = (
        resource_type.removeprefix('google_').replace('_', ' ').title())
    # Uppercase known acronyms.
    resource_type_cleaned = re.sub(
        r'(iam|iap|sql|ssl|tls|url|vpc)',
        lambda m: m.group(1).upper(),
        resource_type_cleaned,
        flags=re.IGNORECASE)
    count = len(resource_names)
    click.echo(
        textwrap.indent(f'{resource_type_cleaned} ({count})', _INDENT_PREFIX))


def terraform_outputs(debug: bool = False):
  """Runs the Terraform output command."""
  cmd = 'terraform output -json'
  _, out, _ = shared.execute_command(
      'Retrieve configuration',
      cmd,
      cwd='./terraform',
      debug_uses_std_out=False,
      debug=debug)
  return out


def update_stage_with_image_digests(stage: shared.StageContext,
                                    debug: bool = False) -> None:
  """Updates the stage file with the latest image digests.

  Args:
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  stage.frontend_image_with_digest = shared.resolve_image_with_digest(
      stage.frontend_image, debug=debug)
  stage.controller_image_with_digest = shared.resolve_image_with_digest(
      stage.controller_image, debug=debug)
  stage.jobs_image_with_digest = shared.resolve_image_with_digest(
      stage.jobs_image, debug=debug)


@click.group()
def cli():
  """Manage your CRMint instance on GCP."""


@cli.command('checklist')
@click.option('--stage_path', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def checklist(stage_path: Union[None, str], debug: bool) -> None:
  """Validates that we can safely deploy CRMint."""
  click.echo(click.style('>>>> Checklist', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = shared.fetch_stage_or_default(stage_path, debug=debug)
  except shared.CannotFetchStageError:
    sys.exit(1)

  # The user needs to be either Owner or Editor with extra roles.
  user_email = shared.get_user_email(debug=debug)
  user_roles = retrieve_user_roles(user_email, stage, debug=debug)
  minimal_roles = [
      'roles/editor',
      'roles/iap.admin',
      'roles/run.admin',
      'roles/compute.networkAdmin',
      'roles/resourcemanager.projectIamAdmin',
      'roles/secretmanager.admin',
  ]
  user_has_enough_roles_to_deploy = any([
      'roles/owner' in user_roles,
      all([role in user_roles for role in minimal_roles])
  ])
  if not user_has_enough_roles_to_deploy:
    missing_roles = set(minimal_roles) - set(user_roles)
    click.secho(textwrap.indent(textwrap.dedent(f"""\
        The user "{user_email}" doesn't have required roles to deploy CRMint.
        Missing IAM roles are: {', '.join(missing_roles)}
        Please contact your administrator to get all these roles.
        """), _INDENT_PREFIX), fg='red', bold=True)
    sys.exit(1)

  if not check_billing_configured(stage, debug=debug):
    click.secho(textwrap.indent(textwrap.dedent("""\
        Please configure your billing account before deploying CRMint:
        https://cloud.google.com/billing/docs/how-to/modify-project#change_the_billing_account_for_a_project
        """), _INDENT_PREFIX), fg='red', bold=True)
    sys.exit(1)

  if not check_billing_enabled(stage, debug=debug):
    click.secho(textwrap.indent(textwrap.dedent("""\
        Please enable billing before deploying CRMint:
        https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project
        """), _INDENT_PREFIX), fg='red', bold=True)
    sys.exit(1)

  click.echo(click.style('Done.', fg='magenta', bold=True))


@cli.command('setup')
@click.option('--stage_path', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def setup(stage_path: Union[None, str], debug: bool) -> None:
  """Setup the GCP environment for CRMint."""
  click.echo(click.style('>>>> Setup', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = shared.fetch_stage_or_default(stage_path, debug=debug)
  except shared.CannotFetchStageError:
    sys.exit(1)

  # Switches workspace.
  patch_etc_hosts(debug=debug)
  terraform_init(debug=debug)
  terraform_switch_workspace(stage, debug=debug)

  # Updates service image digest in the tfvars file to trigger Cloud Run
  # to update the services accordingly.
  update_stage_with_image_digests(stage, debug=debug)

  # Runs setup steps.
  terraform_plan(stage, debug=debug)
  configuration_summary_from_plan(debug=debug)
  terraform_apply(debug=debug)
  unpatch_etc_hosts(debug=debug)
  click.echo(click.style('Done.', fg='magenta', bold=True))


@cli.command('migrate')
@click.option('--stage_path', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def migrate(stage_path: Union[None, str], debug: bool):
  """Migrate the database to the latest schema."""
  del stage_path
  del debug
  click.echo(click.style('Deprecated.', fg='blue', bold=True))


@cli.command('reset')
@click.option('--stage_path', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def reset(stage_path: Union[None, str], debug: bool):
  """Reset pipeline statuses."""
  del stage_path
  del debug
  click.echo(click.style('Deprecated.', fg='blue', bold=True))


@cli.command('url')
@click.option('--stage_path', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def url(stage_path: Union[None, str], debug: bool):
  """Retrieve the frontend URL to access the UI."""
  click.echo(click.style('>>>> CRMint UI', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = shared.fetch_stage_or_default(stage_path, debug=debug)
  except shared.CannotFetchStageError:
    sys.exit(1)

  # Switches workspace.
  terraform_init(debug=debug)
  terraform_switch_workspace(stage, debug=debug)

  # Retrieves outputs from the current Terraform state.
  outputs_json_raw = terraform_outputs(debug=debug)
  outputs = json.loads(outputs_json_raw)

  if not outputs:
    click.secho(f'No state found in current workspace: {stage.project_id}',
                fg='red',
                bold=True)
    click.secho('Fix this by running: $ crmint cloud setup', fg='green')
    sys.exit(1)

  secured_url = outputs['secured_url']['value']
  available_url = shared.wait_for_frontend(secured_url, debug=debug)
  if available_url:
    click.secho(f'Secured url: {available_url}', fg='green', bold=True)
  else:
    # No available url yet.
    sys.exit(1)


if __name__ == '__main__':
  cli()
