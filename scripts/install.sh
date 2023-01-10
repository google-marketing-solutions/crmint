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
CURRENT_DIR=$(pwd)

# Downloads the source code.
if [ ! -d $HOME/crmint ]; then
  git clone https://github.com/google/crmint.git $HOME/crmint
  echo -e "\nCloned crmint repository to your home directory: $HOME."
fi
cd $HOME/crmint

# Updates the targeted branch.
git checkout $TARGET_BRANCH
git pull --rebase

# Resets the virtual environment.
if [ -d .venv ]; then
  rm -r .venv
fi
python -m venv --upgrade-deps .venv

# Installs the command-line.
. .venv/bin/activate
cd ./cli
python -m pip install --require-hashes -r requirements.txt
sudo python -m pip install -e .
deactivate

# Restores initial directory.
cd "$CURRENT_DIR"

# Adds the wrapper function to the user `.bashrc` file.
echo -e "\nAdding a bash function to your $HOME/.bashrc file."
cat <<EOF >$HOME/.crmint
# CRMint wrapper function.
# Automatically activates the virtualenv and makes the command
# accessible from all directories
function crmint {
  CURRENT_DIR=\$(pwd)
  cd $HOME/crmint
  . .venv/bin/activate
  command crmint \$@ || return
  deactivate
  cd "\$CURRENT_DIR"
}

EOF
echo -e "\n# CRMint helpers \nsource \$HOME/.crmint" >> $HOME/.bashrc

# Export CRMint bash function.
# NOTE: this must be used as `source scripts/install.sh master --bundle`
#       in order to expose the added bash crmint function.
source $HOME/.bashrc

# Notifies the user that the command-line is ready.
echo -e "\nSuccessfully installed the CRMint command-line."
echo -e "You can use it now by typing: crmint --help\n"
