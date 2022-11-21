# Copyright 2020 Google Inc
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

FROM mcr.microsoft.com/java/jre-headless:11-zulu-ubuntu
MAINTAINER Alex Prikhodko <aprikhodko@google.com>

ENV CLOUDSDK_CORE_DISABLE_PROMPTS 1
ENV DATA_DIR "/opt/pubsub"
ENV HOST_PORT 8432

RUN apt-get update \
    && apt-get install -y \
        curl bash python \
    # Cleaning
    && rm -rf /var/cache/apt/archives/*.deb \
    && rm -rf /var/lib/apt/lists/*

# Install Google Cloud SDK
COPY install_google_cloud_sdk.bash install_google_cloud_sdk.bash
RUN chmod +x install_google_cloud_sdk.bash
RUN ./install_google_cloud_sdk.bash --disable-prompts
RUN /root/google-cloud-sdk/bin/gcloud config set disable_usage_reporting true
RUN /root/google-cloud-sdk/bin/gcloud components install -q pubsub-emulator beta

RUN mkdir -p ${DATA_DIR}
EXPOSE $HOST_PORT

CMD /root/google-cloud-sdk/bin/gcloud beta emulators pubsub start \
        --data-dir "${DATA_DIR}" \
        --host-port "0.0.0.0:${HOST_PORT}"
