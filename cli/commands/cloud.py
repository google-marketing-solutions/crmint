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
import click
from cli.utils import constants
from cli.utils import shared


GCLOUD = '$GOOGLE_CLOUD_SDK/bin/gcloud --quiet'
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


def fetch_stage_or_default(stage_name=None, debug=False):
  if not stage_name:
    stage_name = shared.get_default_stage_name(debug=debug)
  if not shared.check_stage_file(stage_name):
    click.echo(click.style(
        "Stage file '%s' not found." % stage_name, fg='red', bold=True))
    return None
  stage = shared.get_stage_object(stage_name)
  return stage_name, stage


@click.group()
def cli():
  """Manage your CRMint instance on GCP."""


####################### SETUP #######################


def _check_if_appengine_instance_exists(stage, debug=False):
  project_id = stage.project_id_gae
  cmd = (
      f'{GCLOUD} app describe --verbosity critical --project={project_id}'
      f' | grep -q codeBucket'
  )
  status, _, _ = shared.execute_command(
      'Check if App Engine app already exists',
      cmd, report_empty_err=False, debug=debug)
  return status == 0


def create_appengine(stage, debug=False):
  if _check_if_appengine_instance_exists(stage, debug=debug):
    click.echo('     App Engine app already exists.')
    return
  project_id = stage.project_id_gae
  region = stage.project_region
  cmd = f'{GCLOUD} app create --project={project_id} --region={region}'
  shared.execute_command('Create App Engine instance', cmd, debug=debug)


def _check_if_cloudsql_instance_exists(stage, debug=False):
  project_id = stage.project_id_gae
  db_instance_name = stage.db_instance_name
  cmd = (
      f' {GCLOUD} sql instances list --project={project_id}'
      f" --format='value(name)'"
      f" --filter='name={db_instance_name}'"
  )
  _, out, _ = shared.execute_command(
      'Check if CloudSQL instance already exists',
      cmd, report_empty_err=False, debug=debug)
  return out.strip() == db_instance_name


def create_cloudsql_instance_if_needed(stage, debug=False):
  if _check_if_cloudsql_instance_exists(stage, debug=debug):
    click.echo('     CloudSQL instance already exists.')
    return
  db_instance_name = stage.db_instance_name
  project_id = stage.project_id_gae
  project_sql_region = stage.project_sql_region
  project_sql_tier = stage.project_sql_tier
  cmd = (
      f' {GCLOUD} sql instances create {db_instance_name}'
      f' --tier={project_sql_tier} --region={project_sql_region}'
      f' --project={project_id} --database-version MYSQL_5_7'
      f' --storage-auto-increase'
  )
  shared.execute_command("Creating a CloudSQL instance", cmd, debug=debug)


def _check_if_cloudsql_user_exists(stage, debug=False):
  project_id = stage.project_id_gae
  db_instance_name = stage.db_instance_name
  db_username = stage.db_username
  cmd = (
      f' {GCLOUD} sql users list --project={project_id}'
      f' --instance={db_instance_name}'
      f" --format='value(name)'"
      f" --filter='name={db_username}'"
  )
  _, out, _ = shared.execute_command(
      'Check if CloudSQL user already exists',
      cmd, report_empty_err=False, debug=debug)
  return out.strip() == db_username


def create_cloudsql_user_if_needed(stage, debug=False):
  project_id = stage.project_id_gae
  db_instance_name = stage.db_instance_name
  db_username = stage.db_username
  db_password = stage.db_password
  if _check_if_cloudsql_user_exists(stage, debug=debug):
    click.echo('     CloudSQL user already exists.')
    sql_users_command = 'set-password'
    message = "Setting CloudSQL user's password"
  else:
    sql_users_command = 'create'
    message = 'Creating CloudSQL user'
  cmd = (
      f' {GCLOUD} sql users {sql_users_command} {db_username}'
      f' --host % --instance={db_instance_name} --password={db_password}'
      f' --project={project_id}'
  )
  shared.execute_command(message, cmd, debug=debug)


def _check_if_cloudsql_database_exists(stage, debug=False):
  project_id = stage.project_id_gae
  db_instance_name = stage.db_instance_name
  db_name = stage.db_name
  cmd = (
      f' {GCLOUD} sql databases list --project={project_id}'
      f' --instance={db_instance_name} 2>/dev/null'
      f" --format='value(name)'"
      f" --filter='name={db_name}'"
  )
  _, out, _ = shared.execute_command(
      'Check if CloudSQL database already exists',
      cmd, report_empty_err=False, debug=debug)
  return out.strip() == db_name


def create_cloudsql_database_if_needed(stage, debug=False):
  if _check_if_cloudsql_database_exists(stage, debug=debug):
    click.echo('     CloudSQL database already exists.')
    return
  project_id = stage.project_id_gae
  db_instance_name = stage.db_instance_name
  db_name = stage.db_name
  cmd = (
      f' {GCLOUD} sql databases create {db_name}'
      f' --instance={db_instance_name} --project={project_id}'
  )
  shared.execute_command('Creating CloudSQL database', cmd, debug=debug)


def _get_existing_pubsub_entities(stage, entities, debug=False):
  project_id = stage.project_id_gae
  cmd = (
      f' {GCLOUD} --project={project_id} pubsub {entities} list'
      f' | grep -P ^name:'
  )
  _, out, _ = shared.execute_command(
      f'Fetching list of PubSub {entities}', cmd, debug=debug)
  lines = out.strip().split('\n')
  entities = [l.split('/')[-1] for l in lines]
  return entities


def create_pubsub_topics(stage, debug=False):
  existing_topics = _get_existing_pubsub_entities(stage, 'topics', debug)
  crmint_topics = SUBSCRIPTIONS.keys()
  topics_to_create = [t for t in crmint_topics if t not in existing_topics]
  if not topics_to_create:
    click.echo("     CRMint's PubSub topics already exist")
    return
  project_id = stage.project_id_gae
  topics = ' '.join(topics_to_create)
  cmd = f'{GCLOUD} --project={project_id} pubsub topics create {topics}'
  shared.execute_command(
      "Creating CRMint's PubSub topics", cmd, debug=debug)


def _get_project_number(stage, debug=False):
  project_id = stage.project_id_gae
  cmd = (
      f'{GCLOUD} projects describe {project_id}'
      f' | grep -Po "(?<=projectNumber: .)\d+"'
  )
  _, out, _ = shared.execute_command(
      "Getting project number", cmd, debug=debug)
  return out.strip()

def create_pubsub_subscriptions(stage, debug=False):
  existing_subscriptions = _get_existing_pubsub_entities(
      stage, 'subscriptions', debug)
  project_id = stage.project_id_gae
  service_account = f'{project_id}@appspot.gserviceaccount.com'
  for topic_id in SUBSCRIPTIONS:
    subscription_id = f'{topic_id}-subscription'
    if subscription_id in existing_subscriptions:
      click.echo(f'     PubSub subscription {subscription_id} already exists')
      continue
    subscription = SUBSCRIPTIONS[topic_id]
    if subscription is None:
      continue
    path = subscription['path']
    token = stage.pubsub_verification_token
    push_endpoint = f'https://{project_id}.appspot.com/{path}?token={token}'
    ack_deadline = subscription['ack_deadline_seconds']
    minimum_backoff = subscription['minimum_backoff']
    min_retry_delay = f'{minimum_backoff}s'
    cmd = (
        f' {GCLOUD} --project={project_id} pubsub subscriptions create'
        f' {subscription_id} --topic={topic_id} --topic-project={project_id}'
        f' --ack-deadline={ack_deadline} --min-retry-delay={min_retry_delay}'
        f' --expiration-period=never --push-endpoint={push_endpoint}'
        f' --push-auth-service-account={service_account}'
    )
    shared.execute_command(
        f'Creating PubSub subscription {subscription_id}', cmd, debug=debug)


def grant_pubsub_permissions(stage, debug=False):
  project_id = stage.project_id_gae
  project_number = _get_project_number(stage, debug)
  pubsub_sa = f'service-{project_number}@gcp-sa-pubsub.iam.gserviceaccount.com'
  cmd = (
      f' {GCLOUD} projects add-iam-policy-binding {project_id}'
      f' --member="serviceAccount:{pubsub_sa}"'
      f' --role="roles/iam.serviceAccountTokenCreator"'
  )
  shared.execute_command(
      "Granting Cloud Pub/Sub the permission to create tokens",
      cmd, debug=debug)


def _check_if_scheduler_job_exists(stage, debug=False):
  project_id = stage.project_id_gae
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
    click.echo('     Cloud Scheduler job already exists.')
    return
  project_id = stage.project_id_gae
  cmd = (
      f' {GCLOUD} scheduler jobs create pubsub crmint-cron'
      f" --project={project_id} --schedule='* * * * *'"
      f' --topic=crmint-start-pipeline'
      f' --message-body=\'{{"pipeline_ids": "scheduled"}}\''
      f' --attributes="start_time=0" --description="CRMint\'s cron job"'
  )
  shared.execute_command('Create Cloud Scheduler job', cmd, debug=debug)


def activate_services(stage, debug=False):
  project_id = stage.project_id_gae
  cmd = (
      f' {GCLOUD} services enable --project={project_id}'
      f' analytics.googleapis.com'
      f' analyticsreporting.googleapis.com'
      f' bigquery-json.googleapis.com'
      f' cloudapis.googleapis.com'
      f' logging.googleapis.com'
      f' pubsub.googleapis.com'
      f' storage-api.googleapis.com'
      f' storage-component.googleapis.com'
      f' sqladmin.googleapis.com'
      f' cloudscheduler.googleapis.com'
  )
  shared.execute_command('Activate Cloud services', cmd, debug=debug)


def download_config_files(stage, debug=False):
  stage_file_path = shared.get_stage_file(stage.stage_name)
  cmd = f'cloudshell download-files "{stage_file_path}"'
  shared.execute_command('Download configuration file', cmd, debug=debug)


####################### DEPLOY #######################


def install_required_packages(_, debug=False):
  cmds = [
      'mkdir -p ~/.cloudshell',
      '> ~/.cloudshell/no-apt-get-warning',
      'sudo apt-get install -y rsync libmysqlclient-dev python3-venv',
  ]
  total = len(cmds)
  for i, cmd in enumerate(cmds):
    shared.execute_command(
        f'Install required packages ({i + 1}/{total})', cmd, debug=debug)


def display_workdir(stage, debug=False):
  click.echo("     Working directory: %s" % stage.workdir)


def copy_src_to_workdir(stage, debug=False):
  workdir = stage.workdir
  app_title = stage.app_title
  notification_sender_email = stage.notification_sender_email
  enabled_stages = 'true' if stage.enabled_stages else 'false'
  copy_src_cmd = (
      f' rsync -r --delete'
      f' --exclude=.git'
      f' --exclude=.idea'
      f" --exclude='*.pyc'"
      f' --exclude=frontend/node_modules'
      f' --exclude=backend/data/*.json'
      f' --exclude=tests'
      f' . {workdir}'
  )
  copy_insight_config_cmd = (
      f' cp backend/data/insight.json {workdir}/backend/data/insight.json')
  # copy_db_conf = "echo \'SQLALCHEMY_DATABASE_URI=\"{cloud_db_uri}\"\' > {workdir}/backends/instance/config.py".format(
  #     workdir=stage.workdir,
  #     cloud_db_uri=stage.cloud_db_uri)
  copy_app_data = '\n'.join([
      f'cat > {workdir}/backend/data/app.json <<EOL',
      '{',
      f'  "notification_sender_email": "{notification_sender_email}",',
      f'  "app_title": "{app_title}"',
      '}',
      'EOL',
  ])
  # We dont't use prod environment for the frontend to speed up deploy.
  copy_prod_env = '\n'.join([
      f'cat > {workdir}/frontend/src/environments/environment.ts <<EOL',
      'export const environment = {',
      '  production: true,',
      f'  app_title: "{app_title}",',
      f'  enabled_stages: {enabled_stages}',
      '}',
      'EOL',
  ])
  cmds = [
      copy_src_cmd,
      copy_insight_config_cmd,
      copy_app_data,
      copy_prod_env,
  ]
  total = len(cmds)
  for i, cmd in enumerate(cmds):
    shared.execute_command(
        f'Copy source code to working directory ({i + 1}/{total})',
        cmd, cwd=constants.PROJECT_DIR, debug=debug)


def deploy_frontend(stage, debug=False):
  # NB: Limit the node process memory usage to avoid overloading
  #     the Cloud Shell VM memory which makes it unresponsive.
  project_id = stage.project_id_gae
  max_old_space_size = "$((`free -m | egrep ^Mem: | awk '{print $4}'` / 4 * 3))"
  cmds = [
      ' npm install -g npm@latest',
      (f' NODE_OPTIONS="--max-old-space-size={max_old_space_size}"'
       ' NG_CLI_ANALYTICS=ci npm install --legacy-peer-deps'),
      (f' node --max-old-space-size={max_old_space_size}'
       ' ./node_modules/@angular/cli/bin/ng build'),
      (f' {GCLOUD} --project={project_id} app deploy'
       ' frontend_app.yaml --version=v1'),
  ]
  cmd_workdir = os.path.join(stage.workdir, 'frontend')
  total = len(cmds)
  for i, cmd in enumerate(cmds):
    shared.execute_command(
        f'Deploy frontend service ({i + 1}/{total})',
        cmd, cwd=cmd_workdir, debug=debug)


def deploy_controller(stage, debug=False):
  project_id = stage.project_id_gae
  cloud_db_uri = stage.cloud_db_uri
  pubsub_verification_token = stage.pubsub_verification_token
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
      (f' {GCLOUD} app deploy controller_app_with_env_vars.yaml'
       f' --version=v1 --project={project_id}'),
  ]
  cmd_workdir = os.path.join(stage.workdir, 'backend')
  total = len(cmds)
  for i, cmd in enumerate(cmds):
    shared.execute_command(
        f'Deploy controller service ({i + 1}/{total})',
        cmd, cwd=cmd_workdir, debug=debug)


def deploy_jobs(stage, debug=False):
  project_id = stage.project_id_gae
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
      (f' {GCLOUD} app deploy jobs_app_with_env_vars.yaml'
       f' --version=v1 --project={project_id}'),
  ]
  cmd_workdir = os.path.join(stage.workdir, 'backend')
  total = len(cmds)
  for i, cmd in enumerate(cmds):
    shared.execute_command(
        f'Deploy jobs service ({i + 1}/{total})',
        cmd, cwd=cmd_workdir, debug=debug)


def deploy_dispatch_rules(stage, debug=False):
  project_id = stage.project_id_gae
  cmd = f' {GCLOUD} --project={project_id} app deploy dispatch.yaml'
  cmd_workdir = os.path.join(stage.workdir, 'frontend')
  shared.execute_command(
      'Deploy dispatch rules',
      cmd, cwd=cmd_workdir, debug=debug)


def download_cloud_sql_proxy(_, debug=False):
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


def start_cloud_sql_proxy(stage, debug=False):
  project_id = stage.project_id_gae
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
        f'Start CloudSQL proxy ({i}/{total})',
        cmd,
        cwd='.',
        force_std_out=force_std_out,
        debug=debug)


def stop_cloud_sql_proxy(_, debug=False):
  cmd = "kill -9 $(ps | grep cloud_sql_proxy | awk '{print $1}')"
  shared.execute_command('Stop CloudSQL proxy', cmd, cwd='.', debug=debug)


def install_python_packages(stage, debug=False):
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
        cmd, cwd=cmd_workdir, debug=debug)


def run_db_migrations(stage, debug=False):
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


####################### RESET #######################


def run_reset_pipelines(stage, debug=False):
  _run_flask_command(stage, "Reset statuses of jobs and pipelines",
      flask_command_name="reset-pipelines", debug=debug)


####################### SUB-COMMANDS #################


@cli.command('setup')
@click.option('--stage_name', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def setup(stage_name, debug):
  """Setup the GCP environment for deploying CRMint."""
  click.echo(click.style('>>>> Setup', fg='magenta', bold=True))

  stage_name, stage = fetch_stage_or_default(stage_name, debug=debug)
  if stage is None:
    sys.exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage, stage_name)

  # Runs setup steps.
  components = [
      activate_services,
      create_appengine,
      activate_services,
      create_cloudsql_instance_if_needed,
      create_cloudsql_user_if_needed,
      create_cloudsql_database_if_needed,
      create_pubsub_topics,
      create_pubsub_subscriptions,
      grant_pubsub_permissions,
      create_scheduler_job,
      download_config_files,
  ]
  for component in components:
    component(stage, debug=debug)
  click.echo(click.style('Done.', fg='magenta', bold=True))

# pylint: disable=too-many-arguments
@cli.command('deploy')
@click.option('--stage_name', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
@click.option('--frontend', is_flag=True, default=False)
@click.option('--controller', is_flag=True, default=False)
@click.option('--jobs', is_flag=True, default=False)
@click.option('--dispatch_rules', is_flag=True, default=False)
@click.option('--db_migrations', is_flag=True, default=False)
def deploy(stage_name, debug, frontend, controller, jobs, dispatch_rules,
    db_migrations):
  """Deploy CRMint on GCP."""
  click.echo(click.style('>>>> Deploy', fg='magenta', bold=True))

  stage_name, stage = fetch_stage_or_default(stage_name, debug=debug)
  if stage is None:
    click.echo(click.style(
      'Fix that issue by running: $ crmint cloud setup', fg='green'))
    sys.exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage, stage_name)

  # If no specific components were specified for deploy, then deploy all.
  if not (frontend or controller or jobs or dispatch_rules or db_migrations):
    frontend = True
    controller = True
    jobs = True
    dispatch_rules = True
    db_migrations = True

  # Runs deploy steps.
  components = [
      install_required_packages,
      display_workdir,
      copy_src_to_workdir,
  ]
  if frontend:
    components.append(deploy_frontend)
  if controller:
    components.append(deploy_controller)
  if jobs:
    components.append(deploy_jobs)
  if dispatch_rules:
    components.append(deploy_dispatch_rules)
  if db_migrations:
    components.extend([
        download_cloud_sql_proxy,
        start_cloud_sql_proxy,
        install_python_packages,
        run_db_migrations,
        stop_cloud_sql_proxy,
    ])

  for component in components:
    component(stage, debug=debug)
  click.echo(click.style("Done.", fg='magenta', bold=True))
# pylint: enable=too-many-arguments


@cli.command('reset')
@click.option('--stage_name', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def reset(stage_name, debug):
  """Reset pipeline statuses."""
  click.echo(click.style(">>>> Reset pipelines", fg='magenta', bold=True))

  stage_name, stage = fetch_stage_or_default(stage_name, debug=debug)
  if stage is None:
    click.echo(click.style('Fix that issue by running: `$ crmint cloud setup`', fg='green'))
    sys.exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage, stage_name)

  # Runs setup stages.
  components = [
      install_required_packages,
      display_workdir,
      copy_src_to_workdir,
      install_backends_dependencies,
      download_cloud_sql_proxy,
      start_cloud_sql_proxy,
      prepare_flask_envars,
      run_reset_pipelines,
      stop_cloud_sql_proxy,
  ]
  for component in components:
    component(stage, debug=debug)
  click.echo(click.style('Done.', fg='magenta', bold=True))


if __name__ == '__main__':
  cli()
