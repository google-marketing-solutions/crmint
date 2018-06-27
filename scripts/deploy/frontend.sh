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

# ------------------------- DEPLOY FRONTEND ------------------------
echo
echo -e "$BLUE==>$NONE$BOLD Deploy frontend is started$NONE"
cd $workdir/frontend

npm install
ng build --prod

$gcloud_sdk_dir/bin/gcloud --quiet --project $project_id_gae app deploy gae.yaml --version=v1

# ------------------------- END DEPLOY FRONTEND --------------------
