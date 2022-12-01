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

"""The app module, containing the app factory function."""

import os
from typing import Any, Optional

from flask import Flask

from controller import extensions
from controller import job
from controller import pipeline
from controller import result
from controller import stage
from controller import starter
from controller import views


def create_app(config: Optional[dict[str, Any]] = None) -> Flask:
  """An application factory.

  Args:
    config: Dictionary of config flags to update the app with.

  Returns:
    The configured Flask application.
  """
  app = Flask(__name__)
  app.config['SQLALCHEMY_ECHO'] = bool(int(os.getenv('SQLALCHEMY_ECHO', '0')))
  app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
      'DATABASE_URI',
      'mysql+mysqlconnector://crmint:crmint@db:3306/crmint_development')
  if config:
    app.config.update(**config)
  register_extensions(app)
  register_blueprints(app)
  return app


def register_extensions(app):
  """Register Flask extensions."""
  extensions.cors.init_app(app)
  extensions.db.init_app(app)
  extensions.migrate.init_app(app, extensions.db)


def register_blueprints(app):
  """Register Flask blueprints."""
  app.register_blueprint(views.blueprint, url_prefix='/api')
  app.register_blueprint(pipeline.views.blueprint, url_prefix='/api')
  app.register_blueprint(job.views.blueprint, url_prefix='/api')
  app.register_blueprint(stage.views.blueprint, url_prefix='/api')
  app.register_blueprint(result.views.blueprint)
  app.register_blueprint(starter.views.blueprint)
