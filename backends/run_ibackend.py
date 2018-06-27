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

"""Create an IBackend instance"""
import appengine_config

from flask.helpers import get_debug_flag

import flask_tasks
from ibackend.app import create_app
from ibackend.config import DevConfig, ProdConfig
from ibackend.extensions import api


CONFIG = DevConfig if get_debug_flag() else ProdConfig

app = create_app(api, config_object=CONFIG)
flask_tasks.add(app)
