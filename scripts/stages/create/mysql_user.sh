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

# ------------------------- CREATE USER MYSQL ------------------------
echo
echo -e "$BLUE==>$NONE$BOLD Creating MySQL user is started$NONE"

# Create sql user
$gcloud_sdk_dir/bin/gcloud sql users create $db_username % --instance $db_instance_name --password $db_password --project $project_id_gae --quiet

# ------------------------- END USER MYSQL --------------------------
