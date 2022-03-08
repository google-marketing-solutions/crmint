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

"""Extensions module for backend service.

Each extension is initialized in the app factory located in app.py.
"""


from flask_cors import CORS
from flask_migrate import Migrate
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy


cors = CORS()
db = SQLAlchemy()
migrate = Migrate()
api = Api()  # Default blueprint.


def set_global_api_blueprint(api_blueprint):
  global api  # pylint: disable=global-statement
  api = api_blueprint
