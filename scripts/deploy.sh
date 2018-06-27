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
  echo "Usage: $0 deploy <stage> [options]"
  echo
  echo -e "${BOLD}OPTIONS${NONE}"
  echo "   -a, --all                  Deploy all"
  echo "   --frontend                 Deploy only frontend"
  echo "   --ibackend                 Deploy only ibackend"
  echo "   --jbackend                 Deploy only jbackend"
  echo "   --migration                Deploy only migrations"
  echo "   --cron                     Deploy only cron file"
  echo "   --use_service_account      Deploy using service account as credential file"
  echo "   --reset_pipeline           Reset Job statuses in Pipeline"
  echo "   --db_seeds                 Add seeds to DB"
  echo
}

##########################################################################
# COMMANDS                                                               #
##########################################################################

before_hook() {
  # Load stage variables
  source "$SCRIPTS_DIR/variables/stages/$stage.sh"

  # Load before hook
  source "$SCRIPTS_DIR/deploy/before_hook.sh"
}

before_task() {
  source "$SCRIPTS_DIR/deploy/before_task.sh"
}

deploy_frontend() {
  before_hook
  source "$SCRIPTS_DIR/deploy/frontend.sh"
}

deploy_ibackend() {
  before_hook
  source "$SCRIPTS_DIR/deploy/ibackend.sh"
}

deploy_jbackend() {
  before_hook
  source "$SCRIPTS_DIR/deploy/jbackend.sh"
}

deploy_migration() {
  before_hook
  source "$SCRIPTS_DIR/deploy/migration.sh"
}

deploy_cron() {
  before_hook
  source "$SCRIPTS_DIR/deploy/cron.sh"
}

deploy_all() {
  deploy_frontend
  deploy_ibackend
  deploy_jbackend
  deploy_cron
  deploy_migration
}

db_seeds() {
  before_hook
  before_task
  cp "$SCRIPTS_DIR/deploy/tasks/seeds.py" "$workdir/backends/"
  task_path="$workdir/backends/seeds.py"
  python $task_path
  source "$SCRIPTS_DIR/deploy/after_task.sh"
  rm -f $task_path
}

reset_pipeline() {
  before_hook
  before_task
  cp "$SCRIPTS_DIR/deploy/tasks/reset_pipeline.py" "$workdir/backends/"
  task_path="$workdir/backends/reset_pipeline.py"
  python $task_path
  source "$SCRIPTS_DIR/deploy/after_task.sh"
  rm -f $task_path
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

while [ "$2" != "" ]; do
  case $2 in
    -a | --all )
                            deploy_all
                            break
                            ;;
    --db_seeds )
                            db_seeds
                            ;;
    --reset_pipeline )
                            reset_pipeline $3
                            ;;
    --use_service_account ) use_sa=1
                            ;;
    --frontend )            deploy_frontend
                            ;;
    --ibackend )            deploy_ibackend
                            ;;
    --migration )           deploy_migration
                            ;;
    --jbackend )            deploy_jbackend
                            ;;
    --cron )                deploy_cron
                            ;;
    -h | --help )           display_help
                            exit
                            ;;
    * )                     display_help
                            exit 1
  esac
  shift
done
