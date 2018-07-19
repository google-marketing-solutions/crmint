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

if [ "$1" == "" ]; then
  echo "Usage: $0 stages setup <stage_name>"
  echo
  exit
fi

STAGE_NAME=$1
project_id_gae=`gcloud config get-value project 2>/dev/null`
stage="$SCRIPTS_DIR/variables/stages/${STAGE_NAME}.sh"

if [ -f "$SCRIPTS_DIR/variables/stages/$1.sh" ]; then
  echo "Stage file '${stage}' already exists."
else
  echo
  echo -e -n "$BLUE==>$NONE$BOLD Creating stage description file "
  echo -e "${stage}$NONE"

  echo "project_id_gae=$project_id_gae" > $stage
  echo 'service_account_file="${project_id_gae}.json"' >> $stage
  echo "project_region=europe-west" >> $stage
  echo "project_sql_region=europe-west1" >> $stage
  echo "project_sql_tier=db-g1-small" >> $stage
  echo 'workdir="/tmp/$project_id_gae"' >> $stage
  echo 'db_name=crmintapp' >> $stage
  echo 'db_username=crmintapp' >> $stage
  echo "db_password=`date +%s%N | sha256sum | base64 | head -c 32`" >> $stage
  echo 'db_instance_name=crmintapp' >> $stage
  echo 'db_instance_conn_name="$project_id_gae:$project_sql_region:$db_instance_name"' \
    >> $stage
  echo "notification_sender_email=noreply@${project_id_gae}.appspotmail.com" \
    >> $stage
  echo "app_title=''" >> $stage
  echo 'enabled_stages=false' >> $stage
fi
