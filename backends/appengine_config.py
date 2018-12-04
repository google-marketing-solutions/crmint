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

"""
Initialize the App Engine sdk.
"""
from __future__ import print_function

import os
from google.appengine.ext import vendor


# Add any libraries install in the "lib" folder.
PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
vendor.add(os.path.join(PROJECT_DIR, 'lib'))

if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
  dir_rel_path = os.path.dirname(os.path.realpath(__file__))
  vendor.add(os.path.join(dir_rel_path, 'lib_dev'))

  import pkg_resources
  pkg_resources.require("requests==2.18.4")

  from requests_toolbelt.adapters import (
      appengine as requests_toolbelt_appengine)

  # Use the App Engine Requests adapter. This makes sure that Requests uses
  # URLFetch.
  requests_toolbelt_appengine.monkeypatch()
  print("Appengine requests patched")
