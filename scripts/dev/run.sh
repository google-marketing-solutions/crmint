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
  echo "Usage: $0 dev run [command] [options]"
  echo
  echo -e "${BOLD}COMMANDS${NONE}"
  echo "   frontend                   Run frontend"
  echo "   backends                   Run backends"
  echo
  echo -e "${BOLD}OPTIONS${NONE}"
  echo "   -h, --help                 display detailed help."
  echo
}

##########################################################################
# COMMANDS                                                               #
##########################################################################

frontend() {
  cd $PROJECT_DIR/frontend
  npm install
  node_modules/@angular/cli/bin/ng serve
}

backends() {
  cd $PROJECT_DIR/backends
  dev_appserver.py --enable_sendmail=yes --enable_console=yes gae_dev_ibackend.yaml gae_dev_jbackend.yaml
}

##########################################################################
# READ PASSED ARGUMENTS                                                  #
##########################################################################

case $1 in
  frontend )              frontend
                          exit
                          ;;
  backends )              backends
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
