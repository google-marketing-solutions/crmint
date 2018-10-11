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


# ------------------------- CREATE DATABASE in Cloud SQL ------------------------
if gcloud sql databases list --instance="$db_instance_name" 2>/dev/null | egrep -q "^$db_name\s"; then
  echo -e "$BLUE==>$NONE$BOLD MySQL database $db_name exists $NONE"
else
  echo -e "$BLUE==>$NONE$BOLD Creating MySQL database$NONE"

  gcloud sql databases create $db_name --instance $db_instance_name \
    --project $project_id_gae --quiet
fi
# ------------------------- END CREATE DATABASE in Cloud SQL --------------------------
