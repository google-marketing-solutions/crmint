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
  echo "Usage: $0 cloud [command] [options]"
  echo
  echo -e "${BOLD}COMMANDS${NONE}"
  echo "   setup                      Setup cloud services used by CRMint"
  echo "   deploy                     Deploy an instance of CRMint application"
  echo "   reset                      Reset statuses of jobs and pipelines"
  echo
  echo -e "${BOLD}OPTIONS${NONE}"
  echo "   -h, --help                 display detailed help."
  echo
}

##########################################################################
# COMMANDS                                                               #
##########################################################################

setup() {
  source "$SCRIPTS_DIR/cloud/setup.sh" $@
}

deploy() {
  source "$SCRIPTS_DIR/cloud/deploy.sh" $@
}

reset() {
  source "$SCRIPTS_DIR/cloud/reset.sh" $@
}

##########################################################################
# READ PASSED ARGUMENTS                                                  #
##########################################################################

case $1 in
  setup )                 setup
                          exit
                          ;;
  deploy )                deploy
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
