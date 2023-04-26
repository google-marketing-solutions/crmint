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

set -e

TARGET_BRANCH=$1

# Allows advanced users to use their own CLI wrapper docker image.
#
# NOTE: this is only a wrapper image since the `./cli` local directory is
#       mounted on this container and allow you to develop locally.
#
CRMINT_CLI_DOCKER_IMAGE=${CRMINT_CLI_DOCKER_IMAGE:-europe-docker.pkg.dev/instant-bqml-demo-environment/crmint/cli:latest}

# Allows advanced users to change the home directory for crmint repository.
# Defaults to `$HOME/crmint`.
CRMINT_HOME=${CRMINT_HOME:-$HOME/crmint}

# Downloads the source code.
if [ ! -d $CRMINT_HOME ]; then
  git clone https://github.com/google/crmint.git $CRMINT_HOME
  echo -e "\nCloned crmint repository to: $CRMINT_HOME."
else
  echo -e "\nSkip cloning."
fi

# Updates the targeted branch (if it's a git repository only).
if [ -d $CRMINT_HOME/.git ]; then
  CURRENT_DIR=$(pwd)
  cd $CRMINT_HOME

  if [[ `git status --porcelain` ]]; then
    echo "ERROR: Cannot install configure CRMint Command Line because you have local changes."
    echo "       Please commit your changes or stash them before you install our CLI."
    return
  else
    echo -e "\nNo local changes."
  fi

  git checkout $TARGET_BRANCH
  git pull --rebase
  cd "$CURRENT_DIR"
fi

# Adds the wrapper function to our `.crmint` utility file.
echo -e "\nAdding a bash function to your $HOME/.bashrc file."
cat <<EOF > $HOME/.crmint
# Helpers.
function dump_env_for_crmint_cli {
  env_vars=(
    "APP_TITLE"
    "REGION"
    "USE_VPC"
    "DATABASE_TIER"
    "DATABASE_HA_TYPE"
    "FRONTEND_IMAGE"
    "CONTROLLER_IMAGE"
    "JOBS_IMAGE"
  )

  output_file="$CRMINT_HOME/cli/.env"
  touch \$output_file  # Ensures the file exists even if no variables are set.

  for var in "\${env_vars[@]}"
  do
    if [ -n "\${!var}" ]; then
      echo "\${var}=\${!var}" >> \$output_file
    fi
  done
}

# CRMint wrapper function.
function crmint {
  # CloudShell stores gcloud config in a tmp directory at \`\$CLOUDSDK_CONFIG\`.
  # But to also work on local environments we default to the user home config.
  GCLOUD_CONFIG_PATH="\${CLOUDSDK_CONFIG:-\$HOME/.config/gcloud}"
  echo "Using gcloud config: \$GCLOUD_CONFIG_PATH"

  # Updates the env file with current defined env variables.
  dump_env_for_crmint_cli

  # Runs the CLI with mounted volumes (to simplify local developement).
  docker run --rm --interactive --net=host \
    --env-file $CRMINT_HOME/cli/.env \
    -v $CRMINT_HOME/cli:/app/cli \
    -v $CRMINT_HOME/terraform:/app/terraform \
    -v \$GCLOUD_CONFIG_PATH:/root/.config/gcloud \
    $CRMINT_CLI_DOCKER_IMAGE \
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
