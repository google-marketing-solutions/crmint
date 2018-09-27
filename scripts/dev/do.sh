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
  echo "Usage: $0 dev do [command] [options]"
  echo
  echo -e "${BOLD}COMMANDS${NONE}"
  echo "   requirements               Install required Python packages"
  echo "   add_migration              Create a new DB migration"
  echo "   migrations                 Run new DB migrations"
  echo "   seeds                      Run DB seeds script"
  echo "   reset                      Reset jobs and pipelines to status 'idle'"
  echo
  echo -e "${BOLD}OPTIONS${NONE}"
  echo "   -h, --help                 display detailed help."
  echo
}

##########################################################################
# COMMANDS                                                               #
##########################################################################

requirements() {
  cd $PROJECT_DIR/backends
  pip install -r ibackend/requirements.txt -t lib
  pip install -r jbackend/requirements.txt -t lib
  pip install "sphinx==1.7.2" "sphinx-autobuild==0.7.1"
}

add_migration() {
  cd $PROJECT_DIR/backends
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask db revision -m "$*"
}

migrations() {
  cd $PROJECT_DIR/backends
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask db upgrade
}

seeds() {
  cd $PROJECT_DIR/backends
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask db-seeds
}

reset() {
  cd $PROJECT_DIR/backends
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask reset-pipelines
}

##########################################################################
# READ PASSED ARGUMENTS                                                  #
##########################################################################

case $1 in
  requirements )          requirements
                          exit
                          ;;
  add_migration )         add_migration ${@:1}
                          exit
                          ;;
  migrations )            migrations
                          exit
                          ;;
  seeds )                 seeds
                          exit
                          ;;
  reset )                 reset
                          exit
                          ;;
  * )                     display_help
                          exit
                          ;;
esac

while [ "$2" != "" ]; do
  case $2 in
    -h | --help )           display_help
                            exit
                            ;;
  esac
  shift
done
