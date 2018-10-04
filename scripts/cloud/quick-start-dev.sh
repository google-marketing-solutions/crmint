#!/usr/bin/env bash
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

CURRENT_DIR=$(pwd)

# Clones the crmint repository in the home directory.
cd "$HOME"
git clone https://github.com/google/crmint.git
cd crmint

# Switch to the dev branch
git checkout dev

# Configures the GCP project with the resources needed.
bin/app cloud setup

# Deploy the App Engine services.
bin/app cloud deploy

# Restores initial directory.
cd "$CURRENT_DIR"
