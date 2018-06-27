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
  echo "Usage: $0 dev [command] [options]"
  echo
  echo -e "${BOLD}COMMANDS${NONE}"
  echo "   setup                      Setup DB and config files required for local development."
  echo "   run                        Run backend or frontend services."
  echo "   do                         Do local development tasks."
  echo "   console                    Run shell console for backend."
  echo "   dbconsole                  Run DB console for development environment."
  echo
  echo -e "${BOLD}OPTIONS${NONE}"
  echo "   -h, --help                 Display detailed help."
  echo
}

##########################################################################
# COMMANDS                                                               #
##########################################################################

setup() {
  source "$SCRIPTS_DIR/dev/setup.sh"
}

run() {
  export PYTHONPATH="lib"
  source "$SCRIPTS_DIR/dev/run.sh" $@
}

do_it() {
  source "$SCRIPTS_DIR/dev/do.sh" $@
}

console() {
  cd $PROJECT_DIR/backends
  export PYTHONPATH="$gcloud_sdk_dir/platform/google_appengine:lib"
  export FLASK_APP=run_ibackend.py
  export FLASK_DEBUG=1
  export APPLICATION_ID=$local_application_id
  python -m flask shell
}

dbconsole() {
  # Run with default values for Development
  mysql --user=crmintapp --password=crmintapp crmintapp
}

##########################################################################
# READ PASSED ARGUMENTS                                                  #
##########################################################################

case $1 in
  setup )                 setup
                          exit
                          ;;
  run )                   run ${@:2}
                          exit
                          ;;
  do )                    do_it ${@:2}
                          exit
                          ;;
  console )               console
                          exit
                          ;;
  dbconsole )             dbconsole
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
