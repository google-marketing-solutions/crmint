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

from flask import Flask
from controller import pipeline, job, views, stage
from controller.config import ProdConfig
from controller.database import init_engine
from controller.extensions import set_global_api_blueprint, db, cors, migrate


def create_app(api_blueprint, config_object=ProdConfig):
  """An application factory."""
  app = Flask(__name__.split('.')[1], instance_relative_config=True)
  app.config.from_object(config_object)
  # NB: set the global api blueprint before registering all the blueprints
  set_global_api_blueprint(api_blueprint)
  register_extensions(app)
  register_api_blueprints(api_blueprint)
  register_blueprints(app)
  return app


def register_extensions(app):
  """Register Flask extensions."""
  cors.init_app(app)
  db.init_app(app)
  init_engine(app.config['SQLALCHEMY_DATABASE_URI'])
  migrate.init_app(app, db)


def register_api_blueprints(api_blueprint):
  api_blueprint.init_app(pipeline.views.blueprint)
  api_blueprint.init_app(job.views.blueprint)
  api_blueprint.init_app(stage.views.blueprint)


def register_blueprints(app):
  """Register Flask blueprints."""
  app.register_blueprint(views.blueprint, url_prefix='/api')
  app.register_blueprint(pipeline.views.blueprint, url_prefix='/api')
  app.register_blueprint(job.views.blueprint, url_prefix='/api')
  app.register_blueprint(stage.views.blueprint, url_prefix='/api')
