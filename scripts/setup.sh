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

# 1. Brew check
# 2. Install Python 2.7 from brew and pip
# 3. Install pyyaml
# 4. Install flask
# 5. Install Node.js
# 6. Install Angular
# 7. Install MySQL
# 8. Install Google Cloud SDK
# 9. Install GCloud component app-engine-python
# 10. Install Cloud SQL Proxy

if [ ! -x "$(command -v brew)" ]; then
  echo 'You need install Homebrew to continue.'
  echo 'You can use command: /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"'
  echo 'More info here: https://brew.sh'
  exit 1
fi

if [ ! -x "$(command -v python)" ] || [ ! -x "$(command -v pip)" ]; then
  echo "Installing Python 2.7"
  brew install python
else
  echo "Python installed"
fi

if [ -z "$(pip show pyyaml)" ]; then
  echo "Installing python package pyyaml"
  pip install pyyaml
else
  echo "Python package pyyaml installed"
fi

if [ ! -x "$(command -v flask)" ]; then
  echo "Installing Flask"
  pip install Flask
else
  echo "Flask installed"
fi

if [ ! -x "$(command -v node)" ]; then
  echo "Installing Node.js"
  brew install node
else
  echo "Node.js installed"
fi

if [ ! -x "$(command -v ng)" ]; then
  echo "Installing Angular"
  npm install -g @angular/cli
else
  echo "Angular installed"
fi

if [ ! -x "$(command -v mysql)" ]; then
  echo "Installing MySQL"
  brew install mysql
else
  echo "MySQL installed"
fi

if [ ! -x "$(command -v $gcloud_sdk_dir/bin/gcloud)" ]; then
  echo "Installing Google Cloud SDK"
  export CLOUDSDK_CORE_DISABLE_PROMPTS=1
  export CLOUDSDK_INSTALL_DIR=`realpath "$gcloud_sdk_dir/.."`
  mkdir -p $CLOUDSDK_INSTALL_DIR
  curl https://sdk.cloud.google.com | bash
else
  echo "Google Cloud SDK installed"
fi

if [ -x "$(command -v $gcloud_sdk_dir/bin/gcloud)" ] && [[ -z `$gcloud_sdk_dir/bin/gcloud --version | grep "app-engine-python"` ]]; then
  echo 'Installing gcloud component app-engine-python'
  $gcloud_sdk_dir/bin/gcloud components install app-engine-python
else
  echo 'gcloud component app-engine-python installed'
fi

if [ ! -f "$cloud_sql_proxy" ]; then
  echo "Installing Cloud SQL Proxy"
  curl -o /tmp/cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.darwin.amd64
  chmod +x /tmp/cloud_sql_proxy
  mkdir -p `dirname "$cloud_sql_proxy"`
  mv /tmp/cloud_sql_proxy "$cloud_sql_proxy"
else
  echo 'cloud_sql_proxy installed'
fi
