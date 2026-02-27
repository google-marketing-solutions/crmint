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

FROM python:3.9-slim-bullseye AS base
LABEL maintainer="Your Name <you@example.com>"

# Removes output stream buffering, allowing for more efficient logging
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends mysql-client \
    # Cleaning
    && rm -rf /var/cache/apt/archives/*.deb \
    && rm -rf /var/lib/apt/lists/*

##
# Builder stage
#
FROM base as builder

RUN apt-get update \
    && apt-get install -y \
        git build-essential python3-pip \
    # Cleaning
    && rm -rf /var/cache/apt/archives/*.deb \
    && rm -rf /var/lib/apt/lists/*

# TODO(dulacp): use pip-compile to compile a fresh version of dependencies
COPY ./requirements-controller.txt /app/requirements-controller.txt
RUN mkdir -p /install/dependencies
RUN mkdir -p /install/wheels
RUN pip install \
    --require-hashes \
    --disable-pip-version-check \
    --no-cache-dir \
    --target=/install/dependencies \
    -r /app/requirements-controller.txt \
    -f /install/wheels \
    && rm -rf /install/wheels

##
# Production stage
#
FROM base

# Create a non-root user and group
RUN groupadd -r crmint_user && useradd -r -g crmint_user crmint_user

# Copy installed dependencies
RUN mkdir -p /install/dependencies
COPY --from=builder /install/dependencies /install/dependencies
ENV PYTHONPATH="${PYTHONPATH}:/install/dependencies"
ENV PATH="${PATH}:/install/dependencies/bin"

COPY . /app

# Create /app directory and chown to new user (already created by COPY .)
RUN chown -R crmint_user:crmint_user /app \
    && chown -R crmint_user:crmint_user /install/dependencies

USER crmint_user

WORKDIR /app

ENV FLASK_APP controller_app.py
ENV FLASK_ENV production
ENV PORT 5000

RUN chmod +x ./controller_entrypoint.sh
ENTRYPOINT ["./controller_entrypoint.sh"]
