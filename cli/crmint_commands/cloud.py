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
import subprocess
import signal
from glob import glob
from io import StringIO

import click

from crmint_commands.utils import constants
from crmint_commands.utils import shared


def source_stage_file_and_command_script(stage_file, command):
  os.system("""SCRIPTS_DIR="{}"
        source \"{}\"
        source \"{}/deploy/before_hook.sh\"
        source \"{}/deploy/{}.sh\""""
            .format(constants.SCRIPTS_DIR, stage_file,
                    constants.SCRIPTS_DIR,
                    constants.SCRIPTS_DIR, command))


def fetch_stage_or_default(stage_name=None, debug=False):
  if not stage_name:
    stage_name = shared.get_default_stage_name(debug=debug)

  if not shared.check_stage_file(stage_name):
    click.echo(click.style("Stage file '%s' not found." % stage_name, fg='red', bold=True))
    return None

  stage = shared.get_stage_object(stage_name)
  return stage_name, stage


@click.group()
def cli():
  """Manage your CRMint instance on GCP."""
  pass


####################### SETUP #######################


def _check_if_appengine_instance_exists(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} app describe --project={project_id} | grep -q 'codeBucket'".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae)
  status, out, err = shared.execute_command("Check if App Engine already exists",
      command,
      report_empty_err=False,
      debug=debug)
  return status == 0


def create_appengine(stage, debug=False):
  if _check_if_appengine_instance_exists(stage, debug=debug):
    click.echo("     App Engine already exists.")
    return

  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} app create --project={project_id} --region={region}".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae,
      region=stage.project_region)
  shared.execute_command("Create the App Engine instance", command, debug=debug)


def create_service_account_key_if_needed(stage, debug=False):
  if shared.check_service_account_file(stage):
    click.echo("     Service account key already exists.")
    return

  service_account_file = shared.get_service_account_file(stage)
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} iam service-accounts keys create \"{service_account_file}\" \
    --iam-account=\"{project_id}@appspot.gserviceaccount.com\" \
    --key-file-type='json' \
    --project={project_id}".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae,
      service_account_file=service_account_file)
  shared.execute_command("Create the service account key", command, debug=debug)


def _check_if_mysql_instance_exists(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} sql instances list \
    --project={project_id} 2>/dev/null \
    | egrep -q \"^{db_instance_name}\s\"".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae,
      db_instance_name=stage.db_instance_name)
  status, out, err = shared.execute_command("Check if MySQL instance already exists",
      command,
      report_empty_err=False,
      debug=debug)
  return status == 0


def create_mysql_instance_if_needed(stage, debug=False):
  if _check_if_mysql_instance_exists(stage, debug=debug):
    click.echo("     MySQL instance already exists.")
    return

  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} sql instances create {db_instance_name} \
    --tier={project_sql_tier} \
    --region={project_sql_region} \
    --project={project_id} \
    --database-version MYSQL_5_7 \
    --storage-auto-increase".format(
      gcloud_bin=gcloud_command,
      db_instance_name=stage.db_instance_name,
      project_id=stage.project_id_gae,
      project_sql_region=stage.project_sql_region,
      project_sql_tier=stage.project_sql_tier)
  shared.execute_command("Creating MySQL instance", command, debug=debug)


def _check_if_mysql_user_exists(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} sql users list \
    --project={project_id} \
    --instance={db_instance_name} 2>/dev/null \
    | egrep -q \"^{db_username}\s\"".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae,
      db_instance_name=stage.db_instance_name,
      db_username=stage.db_username)
  status, out, err = shared.execute_command("Check if MySQL user already exists",
      command,
      report_empty_err=False,
      debug=debug)
  return status == 0


def create_mysql_user_if_needed(stage, debug=False):
  if _check_if_mysql_user_exists(stage, debug=debug):
    click.echo("     MySQL user already exists.")
    return

  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} sql users create {db_username} \
    --host % \
    --instance={db_instance_name} \
    --password={db_password} \
    --project={project_id}".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae,
      db_instance_name=stage.db_instance_name,
      db_username=stage.db_username,
      db_password=stage.db_password)
  shared.execute_command("Creating MySQL user", command, debug=debug)


def _check_if_mysql_database_exists(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} sql databases list \
    --project={project_id} \
    --instance={db_instance_name} 2>/dev/null \
    | egrep -q \"^{db_name}\s\"".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae,
      db_instance_name=stage.db_instance_name,
      db_name=stage.db_name)
  status, out, err = shared.execute_command("Check if MySQL database already exists",
      command,
      report_empty_err=False,
      debug=debug)
  return status == 0


def create_mysql_database_if_needed(stage, debug=False):
  if _check_if_mysql_database_exists(stage, debug=debug):
    click.echo("     MySQL database already exists.")
    return

  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} sql databases create {db_name} \
    --instance={db_instance_name} \
    --project={project_id}".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae,
      db_instance_name=stage.db_instance_name,
      db_name=stage.db_name)
  shared.execute_command("Creating MySQL database", command, debug=debug)


def activate_services(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  command = "{gcloud_bin} services enable \
    --project={project_id} \
    --async \
    analytics.googleapis.com \
    analyticsreporting.googleapis.com \
    bigquery-json.googleapis.com \
    cloudapis.googleapis.com \
    logging.googleapis.com \
    storage-api.googleapis.com \
    storage-component.googleapis.com \
    sqladmin.googleapis.com".format(
      gcloud_bin=gcloud_command,
      project_id=stage.project_id_gae)
  shared.execute_command("Activate services", command, debug=debug)


def download_config_files(stage, debug=False):
  stage_file_path = shared.get_stage_file(stage.stage_name)
  service_account_file_path = shared.get_service_account_file(stage)
  command = "cloudshell download-files \
    \"{stage_file}\" \
    \"{service_account_file}\"".format(
      stage_file=stage_file_path,
      service_account_file=service_account_file_path)
  shared.execute_command("Download configuration files", command, debug=debug)


####################### DEPLOY #######################


def install_required_packages(stage, debug=False):
  commands = [
      "mkdir -p ~/.cloudshell",
      "> ~/.cloudshell/no-apt-get-warning",
      "sudo apt-get install -y rsync libmysqlclient-dev",
  ]
  total = len(commands)
  idx = 1
  for cmd in commands:
    shared.execute_command("Install required packages (%d/%d)" % (idx, total),
        cmd,
        debug=debug)
    idx += 1


def display_workdir(stage, debug=False):
  click.echo("     Working directory: %s" % stage.workdir)


def copy_src_to_workdir(stage, debug=False):
  copy_src_cmd = "rsync -r --exclude=.git --exclude=.idea --exclude='*.pyc' \
    --exclude=frontend/node_modules --exclude=backends/data/*.json . {workdir}".format(
      workdir=stage.workdir)

  copy_service_account_cmd = "cp backends/data/{service_account_filename} {workdir}/backends/data/service-account.json".format(
      workdir=stage.workdir,
      service_account_filename=stage.service_account_file)

  copy_db_conf = "echo \'SQLALCHEMY_DATABASE_URI=\"{cloud_db_uri}\"\' > {workdir}/backends/instance/config.py".format(
      workdir=stage.workdir,
      cloud_db_uri=stage.cloud_db_uri)

  copy_app_data = """
cat > %(workdir)s/backends/data/app.json <<EOL
{
  "notification_sender_email": "%(notification_sender_email)s",
  "app_title": "%(app_title)s"
}
EOL""".strip() % dict(
    workdir=stage.workdir,
    app_title=stage.app_title,
    notification_sender_email=stage.notification_sender_email)

  # Prod environment for the frontend
  copy_prod_env = """
cat > %(workdir)s/frontend/src/environments/environment.prod.ts <<EOL
export const environment = {
  production: true,
  app_title: "%(app_title)s",
  enabled_stages: %(enabled_stages)s
}
EOL""".strip() % dict(
    workdir=stage.workdir,
    app_title=stage.app_title,
    enabled_stages="true" if stage.enabled_stages else "false")

  commands = [
      copy_src_cmd,
      copy_service_account_cmd,
      copy_db_conf,
      copy_app_data,
      copy_prod_env,
  ]
  total = len(commands)
  idx = 1
  for cmd in commands:
    shared.execute_command("Copy source code to working directory (%d/%d)" % (idx, total),
        cmd,
        cwd=constants.PROJECT_DIR,
        debug=debug)
    idx += 1


def deploy_frontend(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  commands = [
      "npm install",
      "node_modules/@angular/cli/bin/ng build --prod",
      "{gcloud_bin} --project={project_id} app deploy gae.yaml --version=v1".format(
          gcloud_bin=gcloud_command,
          project_id=stage.project_id_gae),
      "{gcloud_bin} --project={project_id} app deploy dispatch.yaml".format(
          gcloud_bin=gcloud_command,
          project_id=stage.project_id_gae)
  ]
  total = len(commands)
  idx = 1
  for cmd in commands:
    shared.execute_command("Deploy frontend service (%d/%d)" % (idx, total),
        cmd,
        cwd=constants.FRONTEND_DIR,
        debug=debug)
    idx += 1


def deploy_backends(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  commands = [
      "virtualenv --python=python2 env",
      ". env/bin/activate",
      "mkdir -p lib",
      "pip install -r ibackend/requirements.txt -t lib -q",
      "pip install -r jbackend/requirements.txt -t lib -q",
      # Applying patches requered in GAE environment (alas!).
      "cp -r \"$SCRIPTS_DIR\"/patches/lib/* lib/",
      "find \"{workdir}\" -name '*.pyc' -exec rm {} \;".format(workdir=stage.workdir),
      "{gcloud_bin} --project $project_id_gae app deploy gae_ibackend.yaml --version=v1".format(
          gcloud_bin=gcloud_command),
      "{gcloud_bin} --project $project_id_gae app deploy gae_jbackend.yaml --version=v1".format(
          gcloud_bin=gcloud_command),
      "{gcloud_bin} --project $project_id_gae app deploy cron.yaml".format(
          gcloud_bin=gcloud_command),
      "{gcloud_bin} --project $project_id_gae app deploy \"{workdir}/frontend/dispatch.yaml\"".format(
          gcloud_bin=gcloud_command,
          workdir=stage.workdir),
  ]
  total = len(commands)
  idx = 1
  for cmd in commands:
    shared.execute_command("Deploy backend services (%d/%d)" % (idx, total),
        cmd,
        cwd=constants.BACKENDS_DIR,
        debug=debug)
    idx += 1


def start_cloud_sql_proxy(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  commands = [
      "mkdir -p {cloudsql_dir}".format(cloudsql_dir=stage.cloudsql_dir),
      "{cloud_sql_proxy} -projects{project_id} -instances={db_instance_conn_name} -dir={cloudsql_dir} &".format(
          project_id=stage.project_id_gae,
          cloud_sql_proxy=stage.cloud_sql_proxy,
          cloudsql_dir=stage.cloudsql_dir,
          db_instance_conn_name=stage.db_instance_conn_name),
      "cloud_sql_proxy_pid=$!",
      "echo \"cloud_sql_proxy pid: $cloud_sql_proxy_pid\"",
      "sleep 5",  # Wait for cloud_sql_proxy to start.
  ]
  total = len(commands)
  idx = 1
  for cmd in commands:
    shared.execute_command("Start CloudSQL proxy (%d/%d)" % (idx, total),
        cmd,
        cwd=constants.BACKENDS_DIR,
        debug=debug)
    idx += 1


####################### SUB-COMMANDS #################


@cli.command('setup')
@click.option('--stage_name', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def setup(stage_name, debug):
  """Setup the GCP environment for deploying CRMint."""
  click.echo(click.style(">>>> Setup", fg='magenta', bold=True))

  stage_name, stage = fetch_stage_or_default(stage_name, debug=debug)
  if stage is None:
    exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage, stage_name)

  # Runs setup stages.
  components = [
      create_appengine,
      create_service_account_key_if_needed,
      create_mysql_instance_if_needed,
      create_mysql_user_if_needed,
      create_mysql_database_if_needed,
      activate_services,
      download_config_files,
  ]
  for component in components:
    component(stage, debug=debug)
  click.echo(click.style("Done.", fg='magenta', bold=True))


@cli.command('deploy')
@click.option('--stage_name', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def deploy(stage_name, debug):
  """Deploy CRMint on GCP."""
  click.echo(click.style(">>>> Deploy", fg='magenta', bold=True))

  stage_name, stage = fetch_stage_or_default(stage_name, debug=debug)
  if stage is None:
    click.echo(click.style("Fix that issue by running: $ crmint cloud setup", fg='green'))
    exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage, stage_name)

  # Runs setup stages.
  components = [
      install_required_packages,
      display_workdir,
      copy_src_to_workdir,
      deploy_frontend,
      deploy_backends,
      start_cloud_sql_proxy,
  ]
  for component in components:
    component(stage, debug=debug)
  click.echo(click.style("Done.", fg='magenta', bold=True))


if __name__ == '__main__':
  cli()