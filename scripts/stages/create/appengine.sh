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

# ------------------------- CREATE APPENGINE INSTANCE ------------------------
echo
echo -e "$BLUE==>$NONE$BOLD Creating App Engine instance is started$NONE"

# Create instance
$gcloud_sdk_dir/bin/gcloud app create --quiet --project $project_id_gae --region=$project_region

# Create key for appengine service account
$gcloud_sdk_dir/bin/gcloud iam service-accounts keys create "$SCRIPTS_DIR/../backends/data/$service_account_file" --iam-account="$project_id_gae@appspot.gserviceaccount.com" --key-file-type='json' --quiet --project $project_id_gae

# ------------------------- END CREATE APPENGINE INSTANCE --------------------
