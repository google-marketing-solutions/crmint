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

FROM node:12.16-alpine
MAINTAINER Pierre Dulac <dulacp@google.com>

# Copy the app files
WORKDIR /app
COPY ./frontend/ /app/frontend

# Start
WORKDIR /app/frontend
RUN apk add --no-cache --virtual .bootstrap-deps \
    git \
    && npm install \
    && apk del .bootstrap-deps

VOLUME ["/app/frontend"]

# START DEBUG with bash if needed
#RUN apk add --no-cache bash
# END DEBUG

EXPOSE 4200
CMD node_modules/@angular/cli/bin/ng serve --host 0.0.0.0
