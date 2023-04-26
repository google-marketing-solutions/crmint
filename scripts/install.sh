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

TARGET_BRANCH=$1
RUN_COMMAND=$2
COMMAND_OPTIONS=$3
CURRENT_DIR=$(pwd)

COMMAND=""
if [[ ! -z "$RUN_COMMAND" ]]; then
  case "${RUN_COMMAND}" in
    --bundle)
      COMMAND="crmint bundle install"
      ;;
    *)
      echo "Unknown command: ${RUN_COMMAND}" >&2
      exit 2
      ;;
  esac
  if [[ ! -z "$COMMAND" ]]; then
    echo "Will run the following command after installing the CRMint command line"
    echo " ${COMMAND} ${COMMAND_OPTIONS}"
  fi
fi

# Downloads the source code.
if [ ! -d $HOME/crmint ]; then
  git clone https://github.com/google/crmint.git $HOME/crmint
  echo "\\nCloned crmint repository to your home directory: $HOME."
fi
cd $HOME/crmint

# Updates the targeted branch.
git checkout $TARGET_BRANCH
git pull --quiet --rebase

# Installs the command-line.
if [ ! -d .venv ]; then
  sudo apt-get install -y python3-venv
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install --quiet --upgrade "pip<23.0"
pip install --quiet -e cli/

# Adds the wrapper function to the user `.bashrc` file.
echo -e "\\nAdding a bash function to your $HOME/.bashrc file."
cat <<EOF >>$HOME/.bashrc

# CRMint wrapper function.
# Automatically activates the virtualenv and makes the command
# accessible from all directories
function crmint {
  CURRENT_DIR=\$(pwd)
  cd \$HOME/crmint
  . .venv/bin/activate
  command crmint \$@ || return
  deactivate
  cd "\$CURRENT_DIR"
}
EOF

# Restores initial directory.
cd "$CURRENT_DIR"

# Runs the command line if configured for.
if [[ ! -z "$COMMAND" ]]; then
  hash -r
  eval "${COMMAND} ${COMMAND_OPTIONS}"
else
  echo -e "\nSuccessfully installed the CRMint command-line."
  echo "You can use it now by typing: crmint --help"
  exec bash
fi
