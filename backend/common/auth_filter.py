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


from flask import request, redirect
import requests


def add(app):
  # pylint: disable=unused-variable,inconsistent-return-statements
  @app.before_request
  def before_filter():
    if (request.path.startswith('/_ah/') or  # Start/stop instance.
        request.path.startswith('/push/') or  # Push PubSub message.
        ':' in request.host):  # Dev environment.
      return
    response = requests.head(f'{request.url_root}assets/favicon.ico',
                             cookies=request.cookies)
    if response.status_code != 200:
      return redirect(request.url_root)
