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
if [ ! -d venv ]; then
  virtualenv --python=python2 venv
fi
. venv/bin/activate
pip install --quiet -e cli/

# Adds the wrapper function to the user `.bashrc` file.
echo "\\nAdding a bash function to your $HOME/.bashrc file."
cat <<EOF >>$HOME/.bashrc

# CRMint wrapper function.
# Automatically activates the virtualenv and makes the command
# accessible from all directories
function crmint {
   cd \$HOME/crmint
  . venv/bin/activate
  command crmint \$@ || return
  deactivate
}
EOF

echo "Reloading the shell"
exec bash
