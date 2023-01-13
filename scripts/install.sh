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

# CRMint Install Script
#
# This install script must be used as `source scripts/install.sh`
# if you want to expose the crmint bash function to the
# parent shell session.

TARGET_BRANCH=$1

# Downloads the source code.
if [ ! -d $HOME/crmint ]; then
  git clone https://github.com/google/crmint.git $HOME/crmint
  echo -e "\nCloned crmint repository to your home directory: $HOME."
fi

# Updates the targeted branch.
CURRENT_DIR=$(pwd)
cd $HOME/crmint
git checkout $TARGET_BRANCH
git pull --rebase
cd "$CURRENT_DIR"

# Adds the wrapper function to our `.crmint` utility file.
echo -e "\nAdding a bash function to your $HOME/.bashrc file."
cat <<EOF >$HOME/.crmint
# CRMint wrapper function.
function crmint {
  # CloudShell stores gcloud config in a tmp directory at \`\$CLOUDSDK_CONFIG\`.
  # But to also work on local environments we default to the user home config.
  GCLOUD_CONFIG_PATH="\${CLOUDSDK_CONFIG:-\$HOME/.config/gcloud}"
  echo "Using gcloud config: \$GCLOUD_CONFIG_PATH"

  # Runs the CLI with mounted volumes (to simplify local developement).
  docker run --rm -it --net=host \
    -v \$HOME/crmint/cli:/app/cli \
    -v \$HOME/crmint/terraform:/app/terraform \
    -v \$GCLOUD_CONFIG_PATH:/root/.config/gcloud \
    europe-docker.pkg.dev/instant-bqml-demo-environment/crmint/cli:latest \
    crmint \$@
}

EOF

# Sources our utility file in the user `.bashrc` file.
echo -e "\n# CRMint helpers \nsource \$HOME/.crmint" >> $HOME/.bashrc

# Expose CRMint bash function.
source $HOME/.crmint

# Notifies the user that the command-line is ready.
echo -e "\nSuccessfully installed the CRMint command-line."
echo -e "You will now run for you: crmint --help\n"
crmint --help
