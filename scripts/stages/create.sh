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
  echo "Usage: $0 stages create <stage> [options]"
  echo
  echo -e "${BOLD}OPTIONS${NONE}"
  echo "   -a, --all                  create project in Google Cloud and add instances"
  echo "   --project                  create only project in Google Cloud"
  echo "   --mysql                    create only mysql instance"
  echo "   --mysql-user               create only mysql user"
  echo "   --mysql-db                 create only mysql database"
  echo "   --appengine                create only appengine instance"
  echo
}

##########################################################################
# COMMANDS                                                               #
##########################################################################

before_hook() {
  # Load stage variables
  source "$SCRIPTS_DIR/variables/stages/$stage.sh"
}

project() {
  before_hook
  source "$SCRIPTS_DIR/stages/create/project.sh"
}

appengine() {
  before_hook
  source "$SCRIPTS_DIR/stages/create/appengine.sh"
}

mysql() {
  before_hook
  source "$SCRIPTS_DIR/stages/create/mysql.sh"
}

mysql_user() {
  before_hook
  source "$SCRIPTS_DIR/stages/create/mysql_user.sh"
}

mysql_database() {
  before_hook
  source "$SCRIPTS_DIR/stages/create/mysql_database.sh"
}

create_all() {
  project
  appengine
  mysql
  mysql_user
  mysql_database
}

##########################################################################
# READ PASSED ARGUMENTS                                                  #
##########################################################################

if [ -f "$SCRIPTS_DIR/variables/stages/$1.sh" ]; then
  stage=$1
else
  display_help
  echo "File for stage $1 is not found"
  exit
fi

while [ "$2" != "" ]; do
  case $2 in
    -a | --all )
                            create_all
                            break
                            ;;
    --project )
                            project
                            ;;
    --appengine )
                            appengine
                            ;;
    --mysql )
                            mysql
                            ;;
    --mysql-user )
                            mysql_user
                            ;;
    --mysql-db )
                            mysql_database
                            ;;
    -h | --help )           display_help
                            exit
                            ;;
    * )                     display_help
                            exit 1
  esac
  shift
done
