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


import os
import cachecontrol
from flask import request, redirect
import google.auth.transport.requests
from google.oauth2 import id_token
import requests

_PUBSUB_VERIFICATION_TOKEN = os.getenv('PUBSUB_VERIFICATION_TOKEN')
_REQUEST = google.auth.transport.requests.Request(
    session=cachecontrol.CacheControl(requests.session()))


def add(app):
  # pylint: disable=unused-variable,inconsistent-return-statements
  @app.before_request
  def before_filter():
    # Skip auth filter for instance management and in development environment.
    if (request.path.startswith('/_ah/')  # Start/stop instance.
        or ':808' in request.host):  # Ports 8080/8081 are used in dev env.
      return

    # Authenticate PubSub push messages.
    if request.path.startswith('/push/'):
      # Check if request came from a CRMint's push subscription.
      if request.args.get('token', '') != _PUBSUB_VERIFICATION_TOKEN:
        return 'Invalid request', 400
      # Check if request is signed by PubSub.
      try:
        bearer_token = request.headers.get('Authorization')
        token = bearer_token.split(' ')[1]
        claim = id_token.verify_oauth2_token(token, _REQUEST)
      except Exception as e:  # pylint: disable=broad-except
        return f'Invalid token: {e}', 400
    else:
      # NB: User authentication is handled by Identity-Aware Proxy.
      return
