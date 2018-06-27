#!/bin/bash
#
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

# ------------------------- BEFORE TASK ------------------------

mkdir $cloudsql_dir

echo "SQLALCHEMY_DATABASE_URI=\"$local_db_uri\"" > $workdir/backends/instance/config.py

if [ "$use_sa" != "" ]; then
  $cloud_sql_proxy -projects=$project_id_gae -instances=$db_instance_conn_name -dir=$cloudsql_dir -credential_file=data/service-account.json &
else
  $cloud_sql_proxy -projects=$project_id_gae -instances=$db_instance_conn_name -dir=$cloudsql_dir &
fi
cloud_sql_proxy_pid=$!
echo -e "$BLUE==>$NONE$BOLD Run cloud_sql_proxy with pid $cloud_sql_proxy_pid$NONE"
sleep 4

export FLASK_APP="$workdir/backends/run_ibackend.py"
export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
export APPLICATION_ID="$project_id_gae"

cd $workdir/backends

# ----------------------- END BEFORE TASK ----------------------
