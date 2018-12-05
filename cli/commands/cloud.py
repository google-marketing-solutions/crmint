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

from cli.utils import constants
from cli.utils import shared


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

  copy_insight_config_cmd = "cp backends/data/insight.json {workdir}/backends/data/insight.json".format(
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
      copy_insight_config_cmd,
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
  # NB: Limit the node process memory usage to avoid overloading
  #     the Cloud Shell VM memory which makes it unresponsive.
  commands = [
      "npm install",
      "node --max-old-space-size=512 ./node_modules/@angular/cli/bin/ng build",
      "{gcloud_bin} --project={project_id} app deploy gae.yaml --version=v1".format(
          gcloud_bin=gcloud_command,
          project_id=stage.project_id_gae),
      "{gcloud_bin} --project={project_id} app deploy dispatch.yaml".format(
          gcloud_bin=gcloud_command,
          project_id=stage.project_id_gae)
  ]
  cmd_workdir = os.path.join(stage.workdir, 'frontend')
  total = len(commands)
  idx = 1
  for cmd in commands:
    shared.execute_command("Deploy frontend service (%d/%d)" % (idx, total),
        cmd,
        cwd=cmd_workdir,
        debug=debug)
    idx += 1


def install_backends_dependencies(stage, debug=False):
  commands = [
      "virtualenv --python=python2 env",
      "mkdir -p lib",
      "pip install -r ibackend/requirements.txt -t lib -q",
      "pip install -r jbackend/requirements.txt -t lib -q",
      # Applying patches requered in GAE environment (alas!).
      "cp -r \"%(patches_dir)s\"/lib/* lib/" % dict(patches_dir=constants.PATCHES_DIR),
      "find \"%(workdir)s\" -name '*.pyc' -exec rm {} \;" % dict(workdir=stage.workdir),
  ]
  cmd_workdir = os.path.join(stage.workdir, 'backends')
  total = len(commands)
  idx = 1
  for cmd in commands:
    shared.execute_command("Install backends dependencies (%d/%d)" % (idx, total),
        cmd,
        cwd=cmd_workdir,
        debug=debug)
    idx += 1


def deploy_backends(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  commands = [
      ". env/bin/activate && {gcloud_bin} --project={project_id} app deploy gae_ibackend.yaml --version=v1".format(
          gcloud_bin=gcloud_command,
          project_id=stage.project_id_gae),
      ". env/bin/activate && {gcloud_bin} --project={project_id} app deploy gae_jbackend.yaml --version=v1".format(
          gcloud_bin=gcloud_command,
          project_id=stage.project_id_gae),
      ". env/bin/activate && {gcloud_bin} --project={project_id} app deploy cron.yaml".format(
          gcloud_bin=gcloud_command,
          project_id=stage.project_id_gae),
      ". env/bin/activate && {gcloud_bin} --project={project_id} app deploy \"{workdir}/frontend/dispatch.yaml\"".format(
          gcloud_bin=gcloud_command,
          project_id=stage.project_id_gae,
          workdir=stage.workdir),
  ]
  cmd_workdir = os.path.join(stage.workdir, 'backends')
  total = len(commands)
  idx = 1
  for cmd in commands:
    shared.execute_command("Deploy backend services (%d/%d)" % (idx, total),
        cmd,
        cwd=cmd_workdir,
        debug=debug)
    idx += 1


def download_cloud_sql_proxy(stage, debug=False):
  cloud_sql_proxy_path = "/usr/bin/cloud_sql_proxy"
  if os.path.isfile(cloud_sql_proxy_path):
    os.environ["CLOUD_SQL_PROXY"] = cloud_sql_proxy_path
  else:
    cloud_sql_proxy_path = "{}/bin/cloud_sql_proxy".format(os.environ["HOME"])
    if not os.path.isfile(cloud_sql_proxy_path):
      if not os.path.exists(os.path.dirname(cloud_sql_proxy_path)):
        os.mkdir(os.path.dirname(cloud_sql_proxy_path), 0755)
      cloud_sql_download_link = "https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64"
      download_command = "curl -L {} -o {}".format(cloud_sql_download_link,
                                                   cloud_sql_proxy_path)
      shared.execute_command("Downloading Cloud SQL proxy", download_command,
          debug=debug)
    os.environ["CLOUD_SQL_PROXY"] = cloud_sql_proxy_path


def start_cloud_sql_proxy(stage, debug=False):
  gcloud_command = "$GOOGLE_CLOUD_SDK/bin/gcloud --quiet"
  commands = [
      (
          "mkdir -p {cloudsql_dir}".format(cloudsql_dir=stage.cloudsql_dir),
          False,
      ),
      (
          "echo \"CLOUD_SQL_PROXY=$CLOUD_SQL_PROXY\"",
          False,
      ),
      (
          "$CLOUD_SQL_PROXY -projects={project_id} -instances={db_instance_conn_name} -dir={cloudsql_dir} 2>/dev/null &".format(
              project_id=stage.project_id_gae,
              cloudsql_dir=stage.cloudsql_dir,
              db_instance_conn_name=stage.db_instance_conn_name),
          True,
      ),
      (
          "sleep 5",  # Wait for cloud_sql_proxy to start.
          False
      ),
  ]
  total = len(commands)
  idx = 1
  for comp in commands:
    cmd, force_std_out = comp
    shared.execute_command("Start CloudSQL proxy (%d/%d)" % (idx, total),
        cmd,
        cwd='.',
        force_std_out=force_std_out,
        debug=debug)
    idx += 1


def stop_cloud_sql_proxy(stage, debug=False):
  command = "kill -9 $(ps | grep cloud_sql_proxy | awk '{print $1}')"
  shared.execute_command("Stop CloudSQL proxy",
      command,
      cwd='.',
      debug=debug)


def prepare_flask_envars(stage, debug=False):
  os.environ["PYTHONPATH"] = "{google_sdk_dir}/platform/google_appengine:lib".format(
      google_sdk_dir=os.environ["GOOGLE_CLOUD_SDK"])
  os.environ["FLASK_APP"] = "run_ibackend.py"
  os.environ["FLASK_DEBUG"] = "1"
  os.environ["APPLICATION_ID"] = stage.project_id_gae

  # Use the local Cloud SQL Proxy url
  command = "echo \'SQLALCHEMY_DATABASE_URI=\"{cloud_db_uri}\"\' > {workdir}/backends/instance/config.py".format(
      workdir=stage.workdir,
      cloud_db_uri=stage.local_db_uri)
  shared.execute_command("Configure Cloud SQL proxy settings",
      command,
      cwd='.',
      debug=debug)


def _run_flask_command(stage, step_name, flask_command_name="--help", debug=False):
  cmd_workdir = os.path.join(stage.workdir, 'backends')
  command = ". env/bin/activate && python -m flask {command_name}".format(
      command_name=flask_command_name)
  shared.execute_command(step_name,
      command,
      cwd=cmd_workdir,
      debug=debug)


def run_flask_db_upgrade(stage, debug=False):
  _run_flask_command(stage, "Applying database migrations",
      flask_command_name="db upgrade", debug=debug)


def run_flask_db_seeds(stage, debug=False):
  _run_flask_command(stage, "Sowing DB seeds",
      flask_command_name="db-seeds", debug=debug)


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
  click.echo(click.style(">>>> Setup", fg='magenta', bold=True))

  stage_name, stage = fetch_stage_or_default(stage_name, debug=debug)
  if stage is None:
    exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage, stage_name)

  # Runs setup steps.
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
@click.option('--skip-deploy-backends', is_flag=True, default=False)
@click.option('--skip-deploy-frontend', is_flag=True, default=False)
def deploy(stage_name, debug, skip_deploy_backends, skip_deploy_frontend):
  """Deploy CRMint on GCP."""
  click.echo(click.style(">>>> Deploy", fg='magenta', bold=True))

  stage_name, stage = fetch_stage_or_default(stage_name, debug=debug)
  if stage is None:
    click.echo(click.style("Fix that issue by running: $ crmint cloud setup", fg='green'))
    exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage, stage_name)

  # Runs deploy steps.
  components = [
      install_required_packages,
      display_workdir,
      copy_src_to_workdir,
      install_backends_dependencies,
      deploy_backends,
      deploy_frontend,
      download_cloud_sql_proxy,
      start_cloud_sql_proxy,
      prepare_flask_envars,
      run_flask_db_upgrade,
      run_flask_db_seeds,
      stop_cloud_sql_proxy,
  ]

  if skip_deploy_backends and (deploy_backends in components):
    components.remove(deploy_backends)
  if skip_deploy_frontend and (deploy_frontend in components):
    components.remove(deploy_frontend)

  for component in components:
    component(stage, debug=debug)
  click.echo(click.style("Done.", fg='magenta', bold=True))


@cli.command('reset')
@click.option('--stage_name', type=str, default=None)
@click.option('--debug/--no-debug', default=False)
def reset(stage_name, debug):
  """Reset pipeline statuses."""
  click.echo(click.style(">>>> Reset pipelines", fg='magenta', bold=True))

  stage_name, stage = fetch_stage_or_default(stage_name, debug=debug)
  if stage is None:
    click.echo(click.style("Fix that issue by running: `$ crmint cloud setup`", fg='green'))
    exit(1)

  # Enriches stage with other variables.
  stage = shared.before_hook(stage, stage_name)

  # Runs setup stages.
  components = [
      install_required_packages,
      display_workdir,
      copy_src_to_workdir,
      install_backends_dependencies,
      start_cloud_sql_proxy,
      prepare_flask_envars,
      run_reset_pipelines,
      stop_cloud_sql_proxy,
  ]
  for component in components:
    component(stage, debug=debug)
  click.echo(click.style("Done.", fg='magenta', bold=True))


if __name__ == '__main__':
  cli()
