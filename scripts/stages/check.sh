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
# THE COMMAND LINE HELP                                                  #
##########################################################################

display_help() {
  echo "Usage: $0 stages check <stage> [options]"
  echo
  echo -e "${BOLD}OPTIONS${NONE}"
  echo "   -h, --help                  display detailed help"
  echo
}

##########################################################################
# CHECKING FUNCTIONS                                                     #
##########################################################################

warning() {
  echo -e "${BOLD}!!!${NONE} $1"
  exit 1
}

check_service_account() {
  if [ -z $service_account_name ]; then
    warning 'Variable $service_account_name must not be empty'
  else
    echo 'Variable $service_account_name is ok'
  fi
}

check_project_id_gae() {
  if [ -z $project_id_gae ]; then
    warning 'Variable $project_id_gae must not be empty'
  else
    echo 'Variable $project_id_gae is ok'
  fi
}

check_project_org_id() {
  if ! [ -z $project_org_id ] && ! [[ $project_org_id =~ ^\d+$ ]]; then
    warning 'Variable $project_org_id must be empty or contains digits'
  else
    echo 'Variable $project_org_id is ok'
  fi
}

check_project_region() {
  # TODO: Value must be from region list
  if [ -z $project_region ]; then
    warning 'Variable $project_region must not be empty'
  else
    echo 'Variable $project_region is ok'
  fi
}

check_project_sql_tier() {
  if [ -z $project_sql_tier ]; then
    warning 'Variable $project_sql_tier must not be empty'
  else
    echo 'Variable $project_sql_tier is ok'
  fi
}

check_workdir() {
  # Value must not be the same as the project directory
  if [ -z $workdir ]; then
    warning 'Variable $workdir must not be empty'
  else
    echo 'Variable $workdir is ok'
  fi
}

check_db_name() {
  # Value must not be empty
  if [ -z "$db_name" ]; then
    warning 'Variable $db_name must not be empty'
  else
    echo 'Variable $db_name is ok'
  fi
}

check_db_username() {
  # Value must not be empty
  if [ -z $db_username ]; then
    warning 'Variable $db_username must not be empty'
  else
    echo 'Variable $db_username is ok'
  fi
}

check_db_password() {
  # Value must not be empty
  if [ -z $db_password ]; then
    warning 'Variable $db_password must not be empty'
  else
    echo 'Variable $db_password is ok'
  fi
}

check_db_instance_name() {
  # Value must not be empty
  if [ -z $db_instance_name ]; then
    warning 'Variable $db_instance_name must not be empty'
  else
    echo 'Variable $db_instance_name is ok'
  fi
}

check_db_instance_conn_name() {
  # Value must not be empty
  if [ -z $db_instance_conn_name ]; then
    warning 'Variable $db_instance_conn_name must not be empty'
  else
    echo 'Variable $db_instance_conn_name is ok'
  fi
}

check_notification_sender_email() {
  # Value must not be empty
  if [ -z $notification_sender_email ]; then
    warning 'Variable $notification_sender_email must not be empty'
  else
    echo 'Variable $notification_sender_email is ok'
  fi
}

check_app_title() {
  # Value must not be empty
  if [ -z "$app_title" ]; then
    warning 'Variable $app_title must not be empty'
  else
    echo 'Variable $app_title is ok'
  fi
}

check_enabled_stages() {
  # Value must be false or true only
  if ! [[ $enabled_stages =~ ^true|false$ ]]; then
    warning 'Variable $enabled_stages must be false or true only'
  else
    echo 'Variable $enabled_stages is ok'
  fi
}

check_all() {
  source "$SCRIPTS_DIR/variables/stages/$stage.sh"
  check_service_account
  check_project_id_gae
  check_project_org_id
  check_project_region
  check_project_sql_tier
  check_workdir
  check_db_name
  check_db_username
  check_db_password
  check_db_instance_name
  check_db_instance_conn_name
  check_notification_sender_email
  check_app_title
  check_enabled_stages
}

##########################################################################
# READ PASSED ARGUMENTS                                                  #
##########################################################################

if [ -f "$SCRIPTS_DIR/variables/stages/$1.sh" ]; then
  stage=$1
else
  if [ ! -z $1 ] && [ "${1:0:1}" != "-" ]; then
    echo "File for stage $1 is not found"
  fi
  display_help
  exit
fi

if ! [ -z $stage ]; then
  echo -e "Check started for stage ${BOLD}$stage${NONE}\n"
  check_all
  echo -e "\nCheck succeded"
fi

while [ "$2" != "" ]; do
  case $2 in
    -h | --help )           display_help
                            exit
                            ;;
  esac
  shift
done
