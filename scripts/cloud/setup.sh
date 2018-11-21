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

##########################################################################
# READ PASSED ARGUMENTS                                                  #
##########################################################################

while [ "$1" != "" ]; do
  case $1 in
    -h | --help )           echo "Usage: $0 cloud setup"
                            echo
                            break
  esac
  shift
done

project_id_gae=`gcloud config get-value project 2>/dev/null`
stage="$SCRIPTS_DIR/variables/stages/${project_id_gae}.sh"

# ------------------------- CREATE STAGE DESCRIPTION -------------------------
if [ ! -f $stage ]; then
  echo
  echo -e -n "$BLUE==>$NONE$BOLD Creating stage description file "
  echo -e "scripts/variables/stages/${project_id_gae}.sh$NONE"

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
  app_title=`gcloud projects list | grep $project_id_gae | \
    sed -r 's/^[-a-z0-9_]+\s+(.+?)\s+[0-9]+$/\1/g; s/\s+$//g'`
  echo "app_title='$app_title'" >> $stage
  echo 'enabled_stages=false' >> $stage
fi
# ------------------------- END CREATE STAGE DESCRITION ----------------------
echo
echo -e -n "$BLUE==>$NONE$BOLD Loading stage description file "
echo -e "scripts/variables/stages/${project_id_gae}.sh$NONE"

source "$stage"

echo
# ------------------------- CREATE APPENGINE INSTANCE ------------------------
if gcloud app describe | grep -q 'codeBucket'; then
  echo -e "$BLUE==>$NONE$BOLD App Engine instance exists$NONE"
else
  echo -e "$BLUE==>$NONE$BOLD Creating App Engine instance$NONE"

  gcloud app create --quiet --project $project_id_gae --region=$project_region
fi
# ------------------------- END CREATE APPENGINE INSTANCE --------------------
echo
# ------------------------- CREATE APPENGINE SERVICE ACCOUNT KEY -------------
if [ -f "$SCRIPTS_DIR/../backends/data/$service_account_file" ]; then
  echo -e "$BLUE==>$NONE$BOLD App Engine service account key exists$NONE"
else
  echo -e "$BLUE==>$NONE$BOLD Creating App Engine service account key$NONE"

  gcloud iam service-accounts keys create \
    "$SCRIPTS_DIR/../backends/data/$service_account_file" \
    --iam-account="$project_id_gae@appspot.gserviceaccount.com" \
    --key-file-type='json' --quiet --project $project_id_gae
fi
# ------------------------- END CREATE APPENGINE SERVICE ACCOUNT KEY ---------
echo
# ------------------------- CREATE MYSQL INSTANCE ----------------------------
if gcloud sql instances list 2>/dev/null | egrep -q "^$db_instance_name\s"; then
  echo -e "$BLUE==>$NONE$BOLD MySQL instance $db_instance_name exists$NONE"
else
  echo -e "$BLUE==>$NONE$BOLD Creating MySQL instance$NONE"

  gcloud sql instances create $db_instance_name --tier=$project_sql_tier \
    --region=$project_sql_region --project $project_id_gae --quiet \
    --database-version MYSQL_5_7 --storage-auto-increase
fi
# ------------------------- END CREATE MYSQL INSTANCE ------------------------
echo
# ------------------------- CREATE MYSQL USER --------------------------------
if gcloud sql users list --instance="$db_instance_name" 2>/dev/null | egrep -q "^$db_username\s"; then
  echo -e "$BLUE==>$NONE$BOLD MySQL user $db_username exists$NONE"
else
  echo -e "$BLUE==>$NONE$BOLD Creating MySQL user$NONE"

  gcloud sql users create $db_username --host % --instance $db_instance_name \
    --password $db_password --project $project_id_gae --quiet
fi
# ------------------------- END CREATE MYSQL USER ----------------------------
echo
# ------------------------- CREATE MYSQL DATABASE ----------------------------
if gcloud sql databases list --instance="$db_instance_name" 2>/dev/null | egrep -q "^$db_name\s"; then
  echo -e "$BLUE==>$NONE$BOLD MySQL database $db_name exists $NONE"
else
  echo -e "$BLUE==>$NONE$BOLD Creating MySQL database$NONE"

  gcloud sql databases create $db_name --instance $db_instance_name \
    --project $project_id_gae --quiet
fi
# ------------------------- END CREATE MYSQL DATABASE ------------------------
echo
# ------------------------- ENABLE REQUIRED APIS  ----------------------------
echo -e "$BLUE==>$NONE$BOLD Enabling required APIs$NONE"

gcloud services enable \
  analytics.googleapis.com \
  analyticsreporting.googleapis.com \
  bigquery-json.googleapis.com \
  cloudapis.googleapis.com \
  logging.googleapis.com \
  storage-api.googleapis.com \
  storage-component.googleapis.com \
  sqladmin.googleapis.com \
  --async
# ------------------------- END ENABLE REQUIRED APIS -------------------------
echo
# ----------- DOWNLOAD STAGE CONFIG AND SERVICE ACCOUNT KEY FILES ------------
echo -e "$BLUE==>$NONE$BOLD Download stage config file and service account key file, please$NONE"

cloudshell download-files \
  "$stage" \
  "$SCRIPTS_DIR/../backends/data/$service_account_file"
# --------- END DOWNLOAD STAGE CONFIG AND SERVICE ACCOUNT KEY FILES ----------
echo
