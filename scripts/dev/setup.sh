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

###########################################################################
# Create database and database user                                       #
###########################################################################
if ! mysqlshow -ucrmintapp -pcrmintapp 2>/dev/null | grep -q crmintapp; then
  echo "NOTICE: Root password could be required to create DB and DB user." &&
  sudo mysql << EOF
CREATE DATABASE crmintapp CHARACTER SET utf8;
GRANT ALL PRIVILEGES ON crmintapp.* TO 'crmintapp'@'localhost' IDENTIFIED BY 'crmintapp';
FLUSH PRIVILEGES;
quit
EOF
fi

###########################################################################
# Create an App Engine instance config file from a template               #
###########################################################################
if [ ! -f 'backends/instance/config.py' ]; then
  cp backends/instance/config.py.example backends/instance/config.py
fi

###########################################################################
# Create api-service module's config file from a template                 #
###########################################################################
if [ ! -f 'backends/gae_dev_ibackend.yaml' ]; then
  cp backends/gae_dev_ibackend.yaml.example backends/gae_dev_ibackend.yaml
fi

###########################################################################
# Create job-service module's config file from a template                 #
###########################################################################
if [ ! -f 'backends/gae_dev_jbackend.yaml' ]; then
  cp backends/gae_dev_jbackend.yaml.example backends/gae_dev_jbackend.yaml
fi

###########################################################################
# Create application config file from a template                          #
###########################################################################
if [ ! -f 'backends/data/app.json' ]; then
  cp backends/data/app.json.example backends/data/app.json
fi

###########################################################################
# Create local service account file from a template                       #
###########################################################################
if [ ! -f 'backends/data/service-account.json' ]; then
  cp backends/data/service-account.json.example backends/data/service-account.json
fi

###########################################################################
# Install Python libs requred for development                             #
###########################################################################
pip install -r scripts/dev/requirements.txt -t backends/lib_dev

