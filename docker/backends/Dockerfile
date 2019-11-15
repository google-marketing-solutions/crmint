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

# Docker: Google App Engine

FROM python:2.7.15-alpine3.6
MAINTAINER Pierre Dulac <dulacp@google.com>

WORKDIR /root

# Download Google App Engine SDK
RUN apk add --no-cache --virtual .bootstrap-deps wget ca-certificates \
    && wget -O cloud.tar.gz https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-217.0.0-linux-x86_64.tar.gz \
    && tar xzf cloud.tar.gz \
    && rm cloud.tar.gz \
    && apk del .bootstrap-deps

RUN google-cloud-sdk/install.sh \
      --path-update=true \
      --bash-completion=true --rc-path=/root/.bashrc \
      --additional-components app-engine-python

# Disable updater check for the whole installation.
# Users won't be bugged with notifications to update to the latest version of gcloud.
RUN /root/google-cloud-sdk/bin/gcloud config set core/disable_usage_reporting true \
    && /root/google-cloud-sdk/bin/gcloud config set component_manager/disable_update_check true \
    && /root/google-cloud-sdk/bin/gcloud --version

# Disable updater completely.
# Running `gcloud components update` doesn't really do anything in a union FS.
# Changes are lost on a subsequent run.
RUN sed -i -- 's/\"disable_updater\": false/\"disable_updater\": true/g' /root/google-cloud-sdk/lib/googlecloudsdk/core/config.json

# Make gcloud command accessible
ENV PATH /root/google-cloud-sdk/bin:$PATH
ENV gcloud_sdk_dir /root/google-cloud-sdk

# Add permissions to run the App Engine dev server
RUN chmod +x /root/google-cloud-sdk/platform/google_appengine/dev_appserver.py

# Copy the app files
WORKDIR /app
COPY ./backends/core/requirements.txt /app/backends/core/requirements.txt
COPY ./backends/ibackend/requirements.txt /app/backends/ibackend/requirements.txt
COPY ./backends/jbackend/requirements.txt /app/backends/jbackend/requirements.txt
COPY ./backends/core/requirements_dev.txt /app/backends/core/requirements_dev.txt

# Install python dependencies
WORKDIR /app/backends
RUN apk add --update mariadb-client-libs \
    && apk add --no-cache --virtual .bootstrap-deps \
        bash curl python-dev musl-dev mariadb-dev gcc build-base \
    && pip install -r core/requirements_dev.txt -t lib_dev \
    && pip install -r ibackend/requirements.txt -t lib \
    && pip install -r jbackend/requirements.txt -t lib \
    && pip install "sphinx==1.7.2" "sphinx-autobuild==0.7.1" \
    && pip install Mysql-Python \
    && apk del .bootstrap-deps

# Start
WORKDIR /app
COPY ./backends/ /app/backends

# We need bash to run multiline commands in docker-compose.
RUN apk add --no-cache bash

CMD /root/google-cloud-sdk/platform/google_appengine/dev_appserver.py \
      --skip_sdk_update_check \
      --host 0.0.0.0 \
      --admin_host 0.0.0.0 \
      --enable_sendmail yes \
      --enable_console yes \
      --env_var APPLICATION_ID=$APPLICATION_ID \
      --env_var DATABASE_URI=$DATABASE_URI \
      /app/backends/gae_dev_ibackend.yaml /app/backends/gae_dev_jbackend.yaml
