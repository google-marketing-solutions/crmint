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

import mock
import unittest

from flask_restful import Api
from flask_testing import TestCase

from core import database
from core import extensions
from ibackend.app import create_app as ibackend_create_app
from jbackend.app import create_app as jbackend_create_app


class ModelTestCase(unittest.TestCase):

  SQLALCHEMY_DATABASE_URI = \
      'mysql+mysqldb://crmint:crmint@localhost:3306/crmintapp_test'
  SQLALCHEMY_TRACK_MODIFICATIONS = False

  def setUp(self):
    self._engine = database.init_engine(self.SQLALCHEMY_DATABASE_URI)
    # Load tables schema & seed data
    database.init_db()
    database.load_fixtures()

  def tearDown(self):
    # Ensure next test is in a clean state
    database.BaseModel.session.remove()
    database.BaseModel.metadata.drop_all(bind=self._engine)


class BaseTestCase(TestCase):

  ENV = 'dev'
  DEBUG = True
  SQLALCHEMY_DATABASE_URI = \
      'mysql+mysqldb://crmint:crmint@localhost:3306/crmintapp_test'
  SQLALCHEMY_TRACK_MODIFICATIONS = False

  def create_app(self):
    raise NotImplementedError

  def setUp(self):
    # Load tables schema & seed data
    database.init_db()
    database.load_fixtures()

  def tearDown(self):
    # Ensure next test is in a clean state
    extensions.db.session.remove()
    extensions.db.drop_all()


class IBackendBaseTest(BaseTestCase):

  @mock.patch('google.cloud.logging.Client')
  def create_app(self, patched_client):
    api_blueprint = Api()
    app = ibackend_create_app(api_blueprint, config_object=self)
    app.config['TESTING'] = True
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    return app


class JBackendBaseTest(BaseTestCase):

  @mock.patch('google.cloud.logging.Client')
  def create_app(self, patched_client):
    api_blueprint = Api()
    app = jbackend_create_app(api_blueprint, config_object=self)
    app.config['TESTING'] = True
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    return app
