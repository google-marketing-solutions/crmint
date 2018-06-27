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

# Common variables

if [ -d /google/google-cloud-sdk ]; then
  gcloud_sdk_dir='/google/google-cloud-sdk'
elif [ -d /usr/lib/google-cloud-sdk ]; then
  gcloud_sdk_dir='/usr/lib/google-cloud-sdk'
elif [ -d "$HOME/google-cloud-sdk" ]; then
  gcloud_sdk_dir="$HOME/google-cloud-sdk"
else
  # Specify your directory for Google Cloud SDK
  gcloud_sdk_dir=
fi

if [ -f /usr/bin/cloud_sql_proxy ]; then
  cloud_sql_proxy='/usr/bin/cloud_sql_proxy'
else
  # If it's not Cloud Shell, then we need to download cloud_sql_proxy.
  # Learn more at # https://cloud.google.com/sql/docs/mysql/sql-proxy#install.
  cloud_sql_proxy="$HOME/bin/cloud_sql_proxy"
  if [ ! -f "$cloud_sql_proxy" ]; then
    echo 'Downloading cloud_sql_proxy to ~/bin/'
    mkdir -p "$HOME/bin"
    curl -L https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -o "$cloud_sql_proxy"
    chmod +x $cloud_sql_proxy
  fi
fi

# Specify Project ID in Google App Engine for local runs
# Example: crmintapp-<client>
local_application_id=crmintapp
