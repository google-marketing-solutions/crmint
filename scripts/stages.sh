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
  echo "Usage: $0 stages [command] [options]"
  echo
  echo -e "${BOLD}COMMANDS${NONE}"
  echo "   check                      Check stage"
  echo "   create                     Create new project in Google Cloud and add instances"
  echo "   list                       List your stages defined in scripts/variables/stages directory"
  echo
  echo -e "${BOLD}OPTIONS${NONE}"
  echo "   -h, --help                 display detailed help."
  echo
}

##########################################################################
# COMMANDS                                                               #
##########################################################################

list() {
  for entry in `ls $SCRIPTS_DIR/variables/stages | sed -e 's/\..*$//'`; do
    if ! [ "$entry" == 'example' ]; then
      echo "$entry"
    fi
  done
}

create() {
  source "$SCRIPTS_DIR/stages/create.sh" $@
}

check() {
  source "$SCRIPTS_DIR/stages/check.sh" $@
}

##########################################################################
# READ PASSED ARGUMENTS                                                  #
##########################################################################

case $1 in
  list )                  list
                          exit
                          ;;
  check )                 check ${@:2}
                          exit
                          ;;
  create )                create ${@:2}
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
