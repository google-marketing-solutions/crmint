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

# Build and Deploy for local development
#
# NOTE: This script is only meant to build and deploy locally.

DOCKER_BUILDKIT=1 docker build -t crmint-controller:dev -f ./backend/controller.Dockerfile ./backend
DOCKER_BUILDKIT=1 docker build -t crmint-jobs:dev -f ./backend/jobs.Dockerfile ./backend
DOCKER_BUILDKIT=1 docker build -t crmint-frontend:dev -f ./frontend/Dockerfile ./frontend

# Tags the images with the user repository.
PROJECT_ID=$(gcloud --quiet config list --format="value(core.project)")
docker tag crmint-controller:dev europe-docker.pkg.dev/$PROJECT_ID/crmint/controller:dev
docker tag crmint-jobs:dev europe-docker.pkg.dev/$PROJECT_ID/crmint/jobs:dev
docker tag crmint-frontend:dev europe-docker.pkg.dev/$PROJECT_ID/crmint/frontend:dev

# Pushes the images to your Artifact Registry.
docker push europe-docker.pkg.dev/$PROJECT_ID/crmint/controller:dev
docker push europe-docker.pkg.dev/$PROJECT_ID/crmint/jobs:dev
docker push europe-docker.pkg.dev/$PROJECT_ID/crmint/frontend:dev

# Uses our CLI to update the deployment config (called staging file).
crmint stages create
crmint stages update \
    --version dev \
    --controller_image europe-docker.pkg.dev/$PROJECT_ID/crmint/controller \
    --jobs_image europe-docker.pkg.dev/$PROJECT_ID/crmint/jobs \
    --frontend_image europe-docker.pkg.dev/$PROJECT_ID/crmint/frontend

# Runs a new deployment
crmint cloud setup
crmint cloud url
