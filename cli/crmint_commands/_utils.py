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
"""
  Package for shared methods among the commands
"""

import os
import shutil
from glob import glob
from crmint_commands import _constants


IGNORE_PATTERNS = ("^.idea", "^.git", "*.pyc", "frontend/node_modules",
                   "backends/data/*.json")


def before_hook(stage):
  """
    Method that adds variables to the stage object
    and prepares the working directory
  """
  # Set DB connection variables.
  stage.cloudsql_dir = "/tmp/cloudsql"
  stage.cloud_db_uri = "mysql+mysqldb://{}:{}@/{}?unix_socket=/cloudsql/{}".format(
      stage.db_username, stage.db_password,
      stage.db_name, stage.db_instance_conn_name)

  stage.local_db_uri = "mysql+mysqldb://{}:{}@/{}?unix_socket={}/{}".format(
      stage.db_username, stage.db_password, stage.db_name,
      stage.cloudsql_dir, stage.db_instance_conn_name)
  target_dir = stage.workdir

  if os.path.exists(target_dir):
    shutil.rmtree(target_dir)

  # Copy source code to the working directory.
  shutil.copytree(_constants.PROJECT_DIR, target_dir,
                  ignore=shutil.ignore_patterns(IGNORE_PATTERNS))

  # Create DB config for App Engine application in the cloud.
  db_config_path = "%s/backends/instance/config.py" % stage.workdir
  with open(db_config_path, "w") as db_file:
    db_file.write("SQLALCHEMY_DATABASE_URI=\"%s\"" % stage.cloud_db_uri)

  # Copy service account file for deployment.
  account_file_path = "%s/backends/instance/config.py" % stage.workdir
  if os.path.exists(account_file_path):
    os.remove(account_file_path)

  shutil.copytree("%s/backends/data/%s" % (_constants.PROJECT_DIR,
                                           stage.service_account_file),
                  "%s/backends/instance/config.py" % stage.workdir)
  for file_name in glob("%s/backends/data/service-account.json.*" % stage.workdir):
    os.remove(file_name)

  # Make app_data.json for backends.
  with open("%s/backends/data/app.json" % stage.workdir, "w") as app_file:
    app_file.write("""
            {
              "notification_sender_email": "$notification_sender_email",
              "app_title": "$app_title"
            }
            """)
  # Make environment.prod.ts for frontend
  with open("%s/frontend/src/environments/environment.prod.ts" % stage.workdir, "w") as ts_file:
    ts_file.write("""
            export const environment = {
              production: true,
              app_title: "$app_title",
              enabled_stages: $enabled_stages
            }
            """)
  return stage
