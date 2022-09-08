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

import json
import os
import pathlib
import re
import shutil
import sys
import textwrap
from typing import Tuple, Union

import click
import yaml

from cli.utils import constants
from cli.utils import shared
from cli.utils import vpc_helpers
from cli.utils.constants import GCLOUD

_INDENT_PREFIX = '     '

# TODO(dulacp): use dataclass to leverage typing
SUBSCRIPTIONS = {
    'crmint-start-task': {
        'path': 'push/start-task',
        'ack_deadline_seconds': 600,
        'minimum_backoff': 60,  # seconds
    },
    'crmint-task-finished': {
        'path': 'push/task-finished',
        'ack_deadline_seconds': 60,
        'minimum_backoff': 10,  # seconds
    },
    'crmint-start-pipeline': {
        'path': 'push/start-pipeline',
        'ack_deadline_seconds': 60,
        'minimum_backoff': 10,  # seconds
    },
    'crmint-pipeline-finished': None,
}

SUBSCRIPTION_PUSH_ENDPOINT = 'https://{project_id}.appspot.com/{path}?token={token}'


class CannotFetchStageError(Exception):
  """Raised when the stage file cannot be fetched."""


def fetch_stage_or_default(
    stage_path: Union[None, pathlib.Path],
    debug: bool = False) -> shared.StageContext:
  """Returns the loaded stage context.

  Args:
    stage_path: Stage path to load. If None a default stage path is used.
    debug: Enables the debug mode on system calls.

  Raises:
    CannotFetchStageError: if the stage file can be fetched.
  """
  if not stage_path:
    stage_path = shared.get_default_stage_path(debug=debug)
  if not stage_path.exists():
    click.secho(f'Stage file not found at path: {stage_path}',
                fg='red',
                bold=True)
    click.secho('Fix this by running: $ crmint stages create', fg='green')
    raise CannotFetchStageError(f'Not found at: {stage_path}')

  stage = shared.load_stage(stage_path)
  stage.stage_path = stage_path
  if stage.spec_version != constants.LATEST_STAGE_VERSION:
    click.secho(f'Stage file "{stage_path}" needs to be migrated. '
                f'Current spec_version: {stage.spec_version}, '
                f'latest: {constants.LATEST_STAGE_VERSION}',
                fg='red',
                bold=True)
    click.secho('Fix this by running: $ crmint stages migrate', fg='green')
    raise CannotFetchStageError('Stage file needs migration')

  return stage


@click.group()
def cli():
  """Manage your CRMint instance on GCP."""


####################### SETUP #######################


def get_user_email(debug: bool = False) -> str:
  """Returns the user email configured in the gcloud config.

  Args:
    debug: Enables the debug mode on system calls.
  """
  cmd = f'{GCLOUD} config list --format="value(core.account)"'
  _, out, _ = shared.execute_command(
      'Retrieve gcloud current user',
      cmd,
      debug=debug,
      debug_uses_std_out=False)
  return out.strip()


def check_if_user_is_owner(user_email: str,
                           stage: shared.StageContext,
                           debug: bool = False) -> bool:
  """Returns True if the current gcloud user has roles/owner.

  Args:
    user_email: Email address to check the owner role on.
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  project_number = get_project_number(stage, debug=debug)
  cmd = textwrap.dedent(f"""\
      {GCLOUD} projects get-iam-policy {project_number} \\
          --flatten="bindings[].members" \\
          --filter="bindings.members=user:{user_email}" \\
          --format="value(bindings.role)"
      """)
  _, out, _ = shared.execute_command(
      'Validates current user has roles/owner',
      cmd,
      debug=debug,
      debug_uses_std_out=False)
  return bool(re.search(r'roles/owner', out.strip()))


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


def _check_if_appengine_instance_exists(stage, debug=False):
  project_id = stage.project_id
  cmd = (f'{GCLOUD} app describe --verbosity critical --project={project_id}'
         f' | grep -q codeBucket')
  status, _, _ = shared.execute_command(
      'Check if App Engine app already exists',
      cmd,
      report_empty_err=False,
      debug=debug)
  return status == 0


def create_appengine(stage, debug=False):
  if _check_if_appengine_instance_exists(stage, debug=debug):
    click.echo(
        textwrap.indent('App Engine app already exists.', _INDENT_PREFIX))
    return
  project_id = stage.project_id
  region = stage.project_region
  cmd = f'{GCLOUD} app create --project={project_id} --region={region}'
  shared.execute_command('Create App Engine instance', cmd, debug=debug)


def _check_if_cloudsql_instance_exists(stage, debug=False):
  project_id = stage.database_project
  db_instance_name = stage.database_instance_name
  cmd = (f'{GCLOUD} sql instances list --project={project_id}'
         f' --format="value(name)"'
         f' --filter="name={db_instance_name}"')
  _, out, _ = shared.execute_command(
      'Check if CloudSQL instance already exists',
      cmd,
      report_empty_err=False,
      debug_uses_std_out=False,
      debug=debug)
  return out.strip() == db_instance_name


def create_cloudsql_instance_if_needed(stage, debug=False):
  if _check_if_cloudsql_instance_exists(stage, debug=debug):
    click.echo(
        textwrap.indent('CloudSQL instance already exists.', _INDENT_PREFIX))
    return
  db_instance_name = stage.database_instance_name
  project_id = stage.database_project
  project_sql_region = stage.database_region
  project_sql_tier = stage.database_tier
  network_project = stage.network_project
  network = stage.network
  database_ha_type = stage.database_ha_type
  if stage.use_vpc:
    cmd = textwrap.dedent(f"""\
        {GCLOUD} beta sql instances create {db_instance_name} \\
            --tier={project_sql_tier} \\
            --region={project_sql_region} \\
            --project={project_id} \\
            --database-version MYSQL_5_7 \\
            --storage-auto-increase \\
            --network=projects/{network_project}/global/networks/{network} \\
            --availability-type={database_ha_type} \\
            --no-assign-ip
        """)
    shared.execute_command(
        'Creating a CloudSQL instance (with beta VPC)', cmd, debug=debug)
  else:
    cmd = textwrap.dedent(f"""\
        {GCLOUD} sql instances create {db_instance_name} \\
            --tier={project_sql_tier} \\
            --region={project_sql_region} \\
            --project={project_id} \\
            --database-version MYSQL_5_7 \\
            --storage-auto-increase \\
            --availability-type={database_ha_type}
        """)
    shared.execute_command(
        'Creating a CloudSQL instance (with public IP)', cmd, debug=debug)


def _check_if_cloudsql_user_exists(stage, debug=False):
  project_id = stage.database_project
  db_instance_name = stage.database_instance_name
  db_username = stage.database_username
  cmd = (f'{GCLOUD} sql users list'
         f' --project={project_id}'
         f' --instance={db_instance_name}'
         f' --format="value(name)"'
         f' --filter="name={db_username}"')
  _, out, _ = shared.execute_command(
      'Check if CloudSQL user already exists',
      cmd,
      report_empty_err=False,
      debug_uses_std_out=False,
      debug=debug)
  return out.strip() == db_username


def create_cloudsql_user_if_needed(stage, debug=False):
  project_id = stage.database_project
  db_instance_name = stage.database_instance_name
  db_username = stage.database_username
  db_password = stage.database_password
  if _check_if_cloudsql_user_exists(stage, debug=debug):
    click.echo(textwrap.indent('CloudSQL user already exists.', _INDENT_PREFIX))
    sql_users_command = 'set-password'
    message = 'Setting CloudSQL user\'s password'
  else:
    sql_users_command = 'create'
    message = 'Creating CloudSQL user'
  cmd = (f'{GCLOUD} sql users {sql_users_command} {db_username}'
         f' --host % --instance={db_instance_name} --password={db_password}'
         f' --project={project_id}')
  shared.execute_command(message, cmd, debug=debug)


def _check_if_cloudsql_database_exists(stage, debug=False):
  project_id = stage.database_project
  db_instance_name = stage.database_instance_name
  db_name = stage.database_name
  cmd = (f'{GCLOUD} sql databases list --project={project_id}'
         f' --instance={db_instance_name} 2>/dev/null'
         f' --format="value(name)"'
         f' --filter="name={db_name}"')
  _, out, _ = shared.execute_command(
      'Check if CloudSQL database already exists',
      cmd,
      report_empty_err=False,
      debug_uses_std_out=False,
      debug=debug)
  return out.strip() == db_name


def create_cloudsql_database_if_needed(stage, debug=False):
  if _check_if_cloudsql_database_exists(stage, debug=debug):
    click.echo(
        textwrap.indent('CloudSQL database already exists.', _INDENT_PREFIX))
    return
  project_id = stage.database_project
  db_instance_name = stage.database_instance_name
  db_name = stage.database_name
  cmd = (f'{GCLOUD} sql databases create {db_name}'
         f' --instance={db_instance_name} --project={project_id}')
  shared.execute_command('Creating CloudSQL database', cmd, debug=debug)


def _get_existing_pubsub_entities(stage, entity_name, debug=False) -> list[str]:
  project_id = stage.project_id
  cmd = f'{GCLOUD} --project={project_id} pubsub {entity_name} list'
  _, out, _ = shared.execute_command(
      f'Fetching list of PubSub {entity_name}',
      cmd,
      debug_uses_std_out=False,
      debug=debug)
  return re.findall(rf'{entity_name}/(\S+)', out.strip())


def create_pubsub_topics(stage, debug=False):
  existing_topics = _get_existing_pubsub_entities(stage, 'topics', debug)
  crmint_topics = SUBSCRIPTIONS.keys()
  topics_to_create = [t for t in crmint_topics if t not in existing_topics]
  if not topics_to_create:
    click.echo(textwrap.indent('CRMint\'s PubSub topics already exist',
                               _INDENT_PREFIX))
    return
  project_id = stage.project_id
  topics = ' '.join(topics_to_create)
  cmd = f'{GCLOUD} --project={project_id} pubsub topics create {topics}'
  shared.execute_command(
      'Creating CRMint\'s PubSub topics', cmd, debug=debug)


def get_project_number(stage: shared.StageContext, debug: bool = False) -> str:
  """Returns the project number as a string.

  Args:
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  project_id = stage.project_id
  cmd = textwrap.dedent(f"""\
      {GCLOUD} projects describe {project_id} --format="value(projectNumber)"
      """)
  _, out, _ = shared.execute_command(
      'Getting project number',
      cmd,
      debug_uses_std_out=False,
      debug=debug)
  return out.strip()


def get_cloud_sql_ip(stage: shared.StageContext,
                     debug: bool = False) -> str:
  """Returns IP address of the Cloud SQL instance.

  Args:
    stage: Stage context.
    debug: Enables the debug mode on system calls.
  """
  instance_name = stage.database_instance_name
  cmd = textwrap.dedent(f"""\
      {GCLOUD} sql instances describe {instance_name} \\
          --format="value(ipAddresses.ipAddress)"
      """)
  _, out, _ = shared.execute_command(
      'Getting IP address of the Cloud SQL instance',
      cmd,
      debug_uses_std_out=False,
      debug=debug)
  return out.strip()


def _update_pubsub_subscription_endpoint(*, subscription_id: str,
                                         push_endpoint: str,
                                         service_account: str,
                                         stage: shared.StageContext,
                                         debug: bool) -> None:
  cmd = textwrap.dedent(f"""\
        {GCLOUD} --project={stage.project_id} pubsub subscriptions \\
            modify-push-config {subscription_id} \\
            --push-endpoint={push_endpoint} \\
            --push-auth-service-account={service_account}
        """)
  shared.execute_command('Updating subscription token', cmd, debug=debug)


def create_pubsub_subscriptions(stage, debug=False):
  existing_subscriptions = _get_existing_pubsub_entities(
      stage, 'subscriptions', debug)
  project_id = stage.project_id
  service_account = f'{project_id}@appspot.gserviceaccount.com'
  for topic_id in SUBSCRIPTIONS:
    subscription = SUBSCRIPTIONS[topic_id]
    if subscription is None:
      continue
    subscription_id = f'{topic_id}-subscription'
    push_endpoint = SUBSCRIPTION_PUSH_ENDPOINT.format(
        project_id=project_id,
        path=subscription['path'],
        token=stage.pubsub_verification_token)
    if subscription_id in existing_subscriptions:
      _update_pubsub_subscription_endpoint(
          subscription_id=subscription_id,
          push_endpoint=push_endpoint,
          service_account=service_account,
          stage=stage,
          debug=debug)
      click.echo(textwrap.indent(f'Token updated for subscription '
                                 f'{subscription_id}',
                                 _INDENT_PREFIX))
      continue
    ack_deadline = subscription['ack_deadline_seconds']
    minimum_backoff = subscription['minimum_backoff']
    min_retry_delay = f'{minimum_backoff}s'
    cmd = (f'{GCLOUD} --project={project_id} pubsub subscriptions create'
           f' {subscription_id} --topic={topic_id} --topic-project={project_id}'
           f' --ack-deadline={ack_deadline} --min-retry-delay={min_retry_delay}'
           f' --expiration-period=never --push-endpoint={push_endpoint}'
           f' --push-auth-service-account={service_account}')
    shared.execute_command(
        f'Creating PubSub subscription {subscription_id}', cmd, debug=debug)


def _grant_required_permissions(stage, debug=False):
  project_id = stage.project_id
  project_number = get_project_number(stage, debug)
  commands = [
      textwrap.dedent(f"""\
          {GCLOUD} projects add-iam-policy-binding {project_id} \\
              --member="serviceAccount:{project_number}@cloudbuild.gserviceaccount.com" \\
              --role="roles/storage.objectViewer" \\
              --condition=None
          """),
      textwrap.dedent(f"""\
          {GCLOUD} projects add-iam-policy-binding {project_id} \\
              --role="roles/compute.networkUser" \\
              --member="serviceAccount:service-{project_number}@gcp-sa-vpcaccess.iam.gserviceaccount.com" \\
              --condition=None
          """),
      # Needed for projects created on or before April 8, 2021.
      # Grant the Google-managed service account the `iam.serviceAccountTokenCreator` role.
      textwrap.dedent(f"""\
          {GCLOUD} projects add-iam-policy-binding {project_id} \\
              --role="roles/iam.serviceAccountTokenCreator" \\
              --member="serviceAccount:service-{project_number}@gcp-sa-pubsub.iam.gserviceaccount.com" \\
              --condition=None
          """),
      # TODO(Slony): implement an ad hoc service account for CRMint
      # App Engine app should be run on behalf of a separate
      # service account, and users will explicitly grant permissions to
      # this service account according to their use cases.
      textwrap.dedent(f"""\
          {GCLOUD} projects add-iam-policy-binding {project_id} \\
              --member="serviceAccount:{project_id}@appspot.gserviceaccount.com" \\
              --role="roles/editor" \\
              --condition=None
          """),
  ]
  if stage.use_vpc:
    commands.append(textwrap.dedent(f"""\
        {GCLOUD} projects add-iam-policy-binding {project_id} \\
            --member="serviceAccount:{project_number}@cloudbuild.gserviceaccount.com" \\
            --role="roles/cloudsql.client"
    """))
  for idx, cmd in enumerate(commands):
    shared.execute_command(
        f'Grant required permissions ({idx + 1}/{len(commands)})',
        cmd,
        debug=debug)


def _check_if_scheduler_job_exists(stage, debug=False):
  project_id = stage.project_id
  cmd = (
      f' {GCLOUD} scheduler jobs list --project={project_id} 2>/dev/null'
      f' | grep -q crmint-cron'
  )
  status, _, _ = shared.execute_command(
      'Check if Cloud Scheduler job already exists',
      cmd, report_empty_err=False, debug=debug)
  return status == 0


def create_scheduler_job(stage, debug=False):
  if _check_if_scheduler_job_exists(stage, debug=debug):
    click.echo(
        textwrap.indent('Cloud Scheduler job already exists.', _INDENT_PREFIX))
    return
  project_id = stage.project_id
  cmd = (f'{GCLOUD} scheduler jobs create pubsub crmint-cron'
         f' --project={project_id} --schedule="* * * * *"'
         f' --topic=crmint-start-pipeline'
         f' --message-body=\'{{"pipeline_ids": "scheduled"}}\''
         f' --attributes="start_time=0" --description="CRMint\'s cron job"')
  shared.execute_command('Create Cloud Scheduler job', cmd, debug=debug)


def activate_services(stage, debug=False):
  project_id = stage.project_id
  cmd = (f'{GCLOUD} services enable --project={project_id}'
         f' aiplatform.googleapis.com'
         f' analytics.googleapis.com'
         f' analyticsreporting.googleapis.com'
         f' appengine.googleapis.com'
         f' bigquery-json.googleapis.com'
         f' cloudapis.googleapis.com'
         f' logging.googleapis.com'
         f' pubsub.googleapis.com'
         f' storage-api.googleapis.com'
         f' storage-component.googleapis.com'
         f' sqladmin.googleapis.com'
         f' cloudscheduler.googleapis.com'
         f' servicenetworking.googleapis.com'
         f' cloudbuild.googleapis.com'
         f' compute.googleapis.com'
         f' vpcaccess.googleapis.com')
  shared.execute_command('Activate Cloud services', cmd, debug=debug)


def download_config_files(stage, debug=False):
  cmd = f'cloudshell download-files "{stage.stage_path}"'
  shared.execute_command('Download configuration file', cmd, debug=debug)


####################### DEPLOY #######################


def _install_required_packages(_, debug=False):
  cmds = [
      'mkdir -p ~/.cloudshell',
      '> ~/.cloudshell/no-apt-get-warning',
      'sudo apt-get update',
      'sudo apt-get install -y rsync libmysqlclient-dev python3-venv',
  ]
  total = len(cmds)
  for idx, cmd in enumerate(cmds):
    shared.execute_command(
        f'Install required packages ({idx + 1}/{total})', cmd, debug=debug)


def _display_workdir(stage, debug=False):
  del debug  # Unused parameter.
  click.echo(
      textwrap.indent(f'Working directory: {stage.workdir}', _INDENT_PREFIX))


def display_appengine_url(stage: shared.StageContext, debug: bool = False):
  cmd = f'{GCLOUD} app browse --no-launch-browser'
  _, out, _ = shared.execute_command(
      'CRMint UI', cmd, debug_uses_std_out=False, debug=debug)
  click.echo(textwrap.indent(out, _INDENT_PREFIX))


def _copy_src_to_workdir(stage, debug=False):
  enabled_stages_js_encoded = 'true' if stage.enabled_stages else 'false'

  def _copy_sources() -> Tuple[int, str, str]:
    exclude_patterns = (
        '.git*',
        '*.pyc',
        'node_modules',
        'app.json',
        'tests',
        '*_tests.py',
    )
    shared.copy_tree(constants.PROJECT_DIR,
                     stage.workdir,
                     ignore=shutil.ignore_patterns(*exclude_patterns))
    return 0, 'Copied sources', ''

  def _copy_insight_config() -> Tuple[int, str, str]:
    insight_filepath = pathlib.Path(
        constants.PROJECT_DIR, 'backend/data/insight.json')
    if not insight_filepath.exists():
      return 0, 'No insight.json', ''
    else:
      shutil.copy(
          insight_filepath,
          pathlib.Path(stage.workdir, 'backend/data/insight.json'))
      return 0, 'Copied insight.json', ''

  def _update_app_data() -> Tuple[int, str, str]:
    app_data_filepath = pathlib.Path(stage.workdir, 'backend/data/app.json')
    with open(app_data_filepath, 'w+') as f:
      content = {
          'notification_sender_email': stage.notification_sender_email,
          'app_title': stage.gae_app_title,
      }
      json.dump(content, f, indent=2)
    return 0, 'Updated app.json', ''

  def _update_prod_env() -> Tuple[int, str, str]:
    filepath = pathlib.Path(
        stage.workdir, 'frontend/src/environments/environment.prod.ts')
    with open(filepath, 'w') as f:
      content = textwrap.dedent(f"""\
          export const environment = {{
            production: true,
            app_title: "{stage.gae_app_title}",
            enabled_stages: {enabled_stages_js_encoded}
          }}""")
      f.write(content)
    return 0, 'Updated environment.ts', ''

  cmds = [
      _copy_sources,
      _copy_insight_config,
      _update_app_data,
      _update_prod_env,
  ]
  total = len(cmds)
  for idx, cmd in enumerate(cmds):
    shared.execute_command(
        f'Copy source code to working directory ({idx + 1}/{total})',
        cmd,
        cwd=constants.PROJECT_DIR,
        debug=debug)


def _inject_vpc_connector_config(workdir: str,
                                 config_file: str,
                                 stage: shared.StageContext) -> None:
  """Inserts connector config into GAE YAML configs."""
  gae_project = stage.gae_project
  region = stage.gae_region
  connector = stage.connector
  vpc_name = (f'projects/{gae_project}'
              f'/locations/{region}'
              f'/connectors/{connector}')
  # Connector object with required configurations
  connector_config = {
      'vpc_access_connector': {'name': vpc_name},
  }
  config_filepath = os.path.join(workdir, config_file)
  try:
    with open(config_filepath, 'r') as yaml_read:
      config = yaml.safe_load(yaml_read)
      config.update(connector_config)
    with open(config_filepath, 'w') as yaml_write:
      yaml.safe_dump(config, yaml_write)
  except yaml.YAMLError as err:
    click.echo(
        click.style(
            f'Unable to insert VPC connector config to App Engine '
            f'{config_filepath} with error: {err}',
            fg='red'))
    raise


def _run_frontend_deployment(project_id: shared.ProjectId,
                             cmd_workdir: str,
                             capture_outputs: bool = False,
                             debug: bool = False) -> Tuple[int, str, str]:
  return shared.execute_command(
      'Deploy frontend service',
      textwrap.dedent(f"""\
          {GCLOUD} --project={project_id} app deploy frontend_app.yaml \\
              --version=v1
          """),
      cwd=cmd_workdir,
      capture_outputs=capture_outputs,
      debug=debug)


def deploy_frontend(stage, debug=False):
  """Deploys frontend app."""
  # NB: Limit the node process memory usage to avoid overloading
  #     the Cloud Shell VM memory which makes it unresponsive.
  project_id = stage.project_id
  cmd_workdir = pathlib.Path(stage.workdir, 'frontend').as_posix()

  if stage.use_vpc:
    _inject_vpc_connector_config(cmd_workdir, 'frontend_app.yaml', stage)

  # Prepares the deployment.
  cmds = [
      # CloudShell node version is too old for Angular, let's update it.
      textwrap.dedent("""\
          source /usr/local/nvm/nvm.sh \\
          && nvm install 16.16.0
          """),
      textwrap.dedent("""\
          source /usr/local/nvm/nvm.sh \\
          && nvm use 16.16.0 \\
          && npm install -g npm@latest
          """),
      textwrap.dedent("""\
          source /usr/local/nvm/nvm.sh \\
          && nvm use 16.16.0 \\
          && npm install
          """),
      textwrap.dedent("""\
          source /usr/local/nvm/nvm.sh \\
          && nvm use 16.16.0 \\
          && npm run build -- -c production
          """),
  ]
  total = len(cmds)
  for idx, cmd in enumerate(cmds):
    shared.execute_command(
        f'Prepare frontend deployment ({idx + 1}/{total})',
        cmd,
        cwd=cmd_workdir,
        debug=debug)

  # HACK: Retry once the frontend deployment if a P4SA error is encountered.
  #       https://stackoverflow.com/q/66528149/1886070
  retry_error_predicate = lambda x: x and 'unable to retrieve p4sa' in x.lower()
  status, _, err = _run_frontend_deployment(
      project_id, cmd_workdir, capture_outputs=True)
  if status != 0 and retry_error_predicate(err):
    click.echo(
        textwrap.indent('Detected retriable error. Retrying deployment.',
                        _INDENT_PREFIX))
    _run_frontend_deployment(project_id, cmd_workdir, capture_outputs=False)


def deploy_controller(stage, debug=False):
  """Deploys controller app."""
  project_id = stage.project_id
  pubsub_verification_token = stage.pubsub_verification_token
  cmd_workdir = os.path.join(stage.workdir, 'backend')

  if stage.use_vpc:
    host = get_cloud_sql_ip(stage, debug)
    cloud_db_uri = 'mysql+mysqlconnector://{}:{}@{}:3306/{}'.format(
        stage.database_username,
        stage.database_password,
        host,
        stage.database_name)
    _inject_vpc_connector_config(cmd_workdir, 'controller_app.yaml', stage)
  else:
    cloud_db_uri = stage.cloud_db_uri

  cmds = [
      'cp .gcloudignore-controller .gcloudignore',
      'cp requirements-controller.txt requirements.txt',
      'cp controller_app.yaml controller_app_with_env_vars.yaml',
      '\n'.join([
          'cat >> controller_app_with_env_vars.yaml <<EOL',
          'env_variables:',
          f'  PUBSUB_VERIFICATION_TOKEN: {pubsub_verification_token}',
          f'  DATABASE_URI: {cloud_db_uri}',
          'EOL',
      ]),
      (f'{GCLOUD} app deploy controller_app_with_env_vars.yaml'
       f' --version=v1 --project={project_id}')
  ]
  total = len(cmds)
  for idx, cmd in enumerate(cmds):
    shared.execute_command(
        f'Deploy controller service ({idx + 1}/{total})',
        cmd,
        cwd=cmd_workdir,
        debug=debug)


def deploy_jobs(stage, debug=False):
  """Deploys jobs app."""
  project_id = stage.project_id
  pubsub_verification_token = stage.pubsub_verification_token
  cmds = [
      'cp .gcloudignore-jobs .gcloudignore',
      'cp requirements-jobs.txt requirements.txt',
      'cp jobs_app.yaml jobs_app_with_env_vars.yaml',
      '\n'.join([
          'cat >> jobs_app_with_env_vars.yaml <<EOL',
          'env_variables:',
          f'  PUBSUB_VERIFICATION_TOKEN: {pubsub_verification_token}',
          'EOL',
      ]),
      (f'{GCLOUD} app deploy jobs_app_with_env_vars.yaml'
       f' --version=v1 --project={project_id}'),
  ]
  cmd_workdir = os.path.join(stage.workdir, 'backend')
  total = len(cmds)
  for i, cmd in enumerate(cmds):
    shared.execute_command(
        f'Deploy jobs service ({i + 1}/{total})',
        cmd, cwd=cmd_workdir, debug=debug)


def deploy_dispatch_rules(stage, debug=False):
  project_id = stage.project_id
  cmd = f'{GCLOUD} --project={project_id} app deploy dispatch.yaml'
  cmd_workdir = os.path.join(stage.workdir, 'frontend')
  shared.execute_command(
      'Deploy dispatch rules',
      cmd, cwd=cmd_workdir, debug=debug)


def _download_cloud_sql_proxy(stage, debug=False):
  del stage  # Unused parameter.
  cloud_sql_proxy_path = '/usr/bin/cloud_sql_proxy'
  if os.path.isfile(cloud_sql_proxy_path):
    os.environ['CLOUD_SQL_PROXY'] = cloud_sql_proxy_path
  else:
    cloud_sql_proxy_path = '{}/bin/cloud_sql_proxy'.format(os.environ['HOME'])
    if not os.path.isfile(cloud_sql_proxy_path):
      if not os.path.exists(os.path.dirname(cloud_sql_proxy_path)):
        os.mkdir(os.path.dirname(cloud_sql_proxy_path), 0o755)
      url = 'https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64'
      cmd = f'curl -L {url} -o {cloud_sql_proxy_path}'
      shared.execute_command('Downloading Cloud SQL proxy', cmd, debug=debug)
    os.environ['CLOUD_SQL_PROXY'] = cloud_sql_proxy_path


def _start_cloud_sql_proxy(stage, debug=False):
  project_id = stage.project_id
  cloudsql_dir = stage.cloudsql_dir
  db_instance_conn_name = stage.db_instance_conn_name
  cmds = [
      (f'mkdir -p {cloudsql_dir}'.format(), False),
      ('echo "CLOUD_SQL_PROXY=$CLOUD_SQL_PROXY"', False),
      (
          f' $CLOUD_SQL_PROXY -projects={project_id}'
          f' -instances={db_instance_conn_name}'
          f' -dir={cloudsql_dir} 2>/dev/null &',
          True,
      ),
      # ('sleep 5', False), # Wait for cloud_sql_proxy to start.
  ]
  total = len(cmds)
  for i, (cmd, force_std_out) in enumerate(cmds):
    shared.execute_command(
        f'Start CloudSQL proxy ({i + 1}/{total})',
        cmd,
        cwd='.',
        force_std_out=force_std_out,
        debug=debug)


def _stop_cloud_sql_proxy(_, debug=False):
  cmd = "kill -9 $(ps | grep cloud_sql_proxy | awk '{print $1}')"
  shared.execute_command('Stop CloudSQL proxy', cmd, cwd='.', debug=debug)


def _install_python_packages(stage, debug=False):
  cmds = [
      (' [ ! -d ".venv_controller" ] &&'
       ' python3 -m venv .venv_controller &&'
       ' . .venv_controller/bin/activate &&'
       ' pip install --upgrade pip wheel &&'
       ' deactivate'),
      (' . .venv_controller/bin/activate &&'
       ' pip install -r requirements-controller.txt')
  ]
  cmd_workdir = os.path.join(stage.workdir, 'backend')
  total = len(cmds)
  for i, cmd in enumerate(cmds):
    shared.execute_command(
        f'Install required Python packages ({i + 1}/{total})',
        cmd,
        cwd=cmd_workdir,
        report_empty_err=False,
        debug=debug)


def _run_db_migrations(stage, debug=False):
  local_db_uri = stage.local_db_uri
  env_vars = f'DATABASE_URI="{local_db_uri}" FLASK_APP=controller_app.py'
  cmd = (
      ' . .venv_controller/bin/activate &&'
      f' {env_vars} python -m flask db upgrade &&'
      f' {env_vars} python -m flask db-seeds'
  )
  cmd_workdir = os.path.join(stage.workdir, 'backend')
  shared.execute_command(
      'Applying database migrations', cmd, cwd=cmd_workdir, debug=debug)


def _create_build_worker_pool(stage, debug=False):
  region = stage.project_region
  network_project = stage.network_project
  network = stage.network
  cmd = textwrap.dedent(f"""\
      {GCLOUD} builds worker-pools create crmint-build-workers-{region} \\
          --region={region} \\
          --peered-network=projects/{network_project}/global/networks/{network}
      """)
  shared.execute_command(
      'Creating a Cloud Build worker pool', cmd, debug=debug)


def _delete_build_worker_pool(stage, debug=False):
  region = stage.project_region
  cmd = textwrap.dedent(f"""\
      {GCLOUD} builds worker-pools delete crmint-build-workers-{region} \\
          --region={region}
      """)
  shared.execute_command(
      'Deleting the Cloud Build worker pool', cmd, debug=debug)


def _run_db_migrations_using_build(stage, debug=False):
  project_id = stage.project_id
  region = stage.project_region
  cloud_db_uri = stage.cloud_db_uri
  sql_instance_name = stage.database_instance_name
  sql_region = stage.database_region
  commands = [
      'cp requirements-controller.txt requirements.txt',
      'cp .gcloudignore-migrations .gcloudignore',
      textwrap.dedent(f"""\
          {GCLOUD} builds submit --config cloudmigrate.yaml \\
              --region={region} \\
              --worker-pool=projects/{project_id}/locations/{region}/workerPools/crmint-build-workers-{region} \\
              --substitutions="_CLOUD_DB_URI={cloud_db_uri},_SQL_INSTANCE_NAME={sql_instance_name},_SQL_REGION={sql_region}"
      """),
  ]
  cmd_workdir = os.path.join(stage.workdir, 'backend')
  for idx, cmd in enumerate(commands):
    shared.execute_command(
        f'Applying database migrations ({idx + 1}/{len(commands)})',
        cmd,
        cwd=cmd_workdir,
        debug=debug)


def _run_reset_pipelines(stage, debug=False):
  local_db_uri = stage.local_db_uri
  env_vars = f'DATABASE_URI="{local_db_uri}" FLASK_APP=controller_app.py'
  cmd = (
      ' . .venv_controller/bin/activate &&'
      f' {env_vars} python -m flask reset-pipelines'
  )
  cmd_workdir = os.path.join(stage.workdir, 'backend')
  shared.execute_command(
      'Reset statuses of jobs and pipelines', cmd, cwd=cmd_workdir, debug=debug)


####################### SUB-COMMANDS #################


@cli.command('checklist')
@click.option('--stage_path', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def checklist(stage_path: Union[None, str], debug: bool) -> None:
  """Validates that we can safely deploy CRMint."""
  click.echo(click.style('>>>> Checklist', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = fetch_stage_or_default(stage_path, debug=debug)
  except CannotFetchStageError:
    sys.exit(1)

  user_email = get_user_email(debug=debug)
  if not check_if_user_is_owner(user_email, stage, debug=debug):
    click.secho(textwrap.indent(textwrap.dedent(f"""\
        Missing roles/owner for user ({user_email}), which is needed for
        deploying CRMint. Please contact your administrator to get this role.
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
  """Setup the GCP environment for deploying CRMint."""
  click.echo(click.style('>>>> Setup', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = fetch_stage_or_default(stage_path, debug=debug)
  except CannotFetchStageError:
    sys.exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage)

  # Runs setup steps.
  components = [
      activate_services,
  ]
  if stage.use_vpc:
    components.extend([
        vpc_helpers.create_vpc,
        vpc_helpers.create_subnet,
        vpc_helpers.create_vpc_connector,
    ])
  components.extend([
      create_appengine,
      create_cloudsql_instance_if_needed,
      create_cloudsql_user_if_needed,
      create_cloudsql_database_if_needed,
      create_pubsub_topics,
      create_pubsub_subscriptions,
      _grant_required_permissions,
      create_scheduler_job,
      download_config_files,
  ])
  for component in components:
    component(stage, debug=debug)
  click.echo(click.style('Done.', fg='magenta', bold=True))


@cli.command('deploy')
@click.option('--stage_path', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
@click.option('--frontend', is_flag=True, default=False)
@click.option('--controller', is_flag=True, default=False)
@click.option('--jobs', is_flag=True, default=False)
@click.option('--dispatch_rules', is_flag=True, default=False)
@click.option('--db_migrations', is_flag=True, default=False)
def deploy(stage_path: Union[None, str],
           debug: bool,
           frontend: bool,
           controller: bool,
           jobs: bool,
           dispatch_rules: bool,
           db_migrations: bool) -> None:
  """Deploy CRMint on GCP."""
  click.echo(click.style('>>>> Deploy', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = fetch_stage_or_default(stage_path, debug=debug)
  except CannotFetchStageError:
    sys.exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage)

  # If no specific components were specified for deploy, then deploy all.
  if not (frontend or controller or jobs or dispatch_rules or db_migrations):
    frontend = True
    controller = True
    jobs = True
    dispatch_rules = True
    db_migrations = True

  # Runs deploy steps.
  components = [
      _install_required_packages,
      _display_workdir,
      _copy_src_to_workdir,
  ]
  if frontend:
    components.append(deploy_frontend)
  if db_migrations:
    if stage.use_vpc:
      components.extend([
          _create_build_worker_pool,
          _run_db_migrations_using_build,
          _delete_build_worker_pool,
      ])
    else:
      components.extend([
          _download_cloud_sql_proxy,
          _start_cloud_sql_proxy,
          _install_python_packages,
          _run_db_migrations,
          _stop_cloud_sql_proxy,
      ])
  if controller:
    components.append(deploy_controller)
  if jobs:
    components.append(deploy_jobs)
  if dispatch_rules:
    components.append(deploy_dispatch_rules)

  # Displays the frontend url to improve the user experience.
  components.append(display_appengine_url)
  for component in components:
    component(stage, debug=debug)
  click.echo(click.style('Done.', fg='magenta', bold=True))


@cli.command('reset')
@click.option('--stage_path', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def reset(stage_path: Union[None, str], debug: bool):
  """Reset pipeline statuses."""
  click.echo(click.style('>>>> Reset pipelines', fg='magenta', bold=True))

  if stage_path is not None:
    stage_path = pathlib.Path(stage_path)

  try:
    stage = fetch_stage_or_default(stage_path, debug=debug)
  except CannotFetchStageError:
    sys.exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage)

  # Runs setup stages.
  components = [
      _install_required_packages,
      _display_workdir,
      _copy_src_to_workdir,
      _download_cloud_sql_proxy,
      _start_cloud_sql_proxy,
      _install_python_packages,
      _run_reset_pipelines,
      _stop_cloud_sql_proxy,
  ]
  for component in components:
    component(stage, debug=debug)
  click.echo(click.style('Done.', fg='magenta', bold=True))


if __name__ == '__main__':
  cli()
