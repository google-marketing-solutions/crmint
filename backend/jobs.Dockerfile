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

FROM ubuntu:20.04 AS base
MAINTAINER Alex Prikhodko <aprikhodko@google.com>
MAINTAINER Pierre Dulac <dulacp@google.com>

# Removes output stream buffering, allowing for more efficient logging
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.9 python3-distutils python-is-python3 mysql-client \
    # Set Python 3.9 as the default for python3
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 2 \
    # Cleaning
    && rm -rf /var/cache/apt/archives/*.deb \
    && rm -rf /var/lib/apt/lists/*

##
# Builder stage
#
FROM base as builder

RUN apt-get update \
    && apt-get install -y \
        git build-essential python3.9-dev python3-pip \
    # Cleaning
    && rm -rf /var/cache/apt/archives/*.deb \
    && rm -rf /var/lib/apt/lists/*

# TODO(dulacp): use pip-compile to compile a fresh version of dependencies
COPY ./requirements-jobs.txt /app/requirements-jobs.txt
RUN mkdir -p /install/dependencies
RUN mkdir -p /install/wheels
RUN pip install \
    --require-hashes \
    --disable-pip-version-check \
    --no-cache-dir \
    --target=/install/dependencies \
    -r /app/requirements-jobs.txt \
    -f /install/wheels \
    && rm -rf /install/wheels

##
# Production stage
#
FROM base

# Copy installed dependencies
RUN mkdir -p /install/dependencies
COPY --from=builder /install/dependencies /install/dependencies
ENV PYTHONPATH="${PYTHONPATH}:/install/dependencies"
ENV PATH="${PATH}:/install/dependencies/bin"

COPY . /app

WORKDIR /app

ENV FLASK_APP jobs_app.py
ENV FLASK_ENV production
ENV PORT 5001

CMD gunicorn -b :$PORT -w 3 jobs_app:app
