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

"""Controller app testing utils."""

import os
from unittest import mock

from absl.testing import parameterized
import flask

from controller import app
from controller import database
from controller import extensions
from tests import utils


class ModelTestCase(parameterized.TestCase):
  """Base class for model testing."""

  def setUp(self):
    super().setUp()
    # Pushes an application context manually.
    test_app = flask.Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    extensions.db.init_app(test_app)
    self.ctx = test_app.app_context()
    self.ctx.push()
    # Creates tables & loads seed data
    extensions.db.create_all()

  def tearDown(self):
    super().tearDown()
    # Drops the app context
    self.ctx.pop()


class ControllerAppTest(utils.AppTestCase):
  """Controller app test class."""

  @mock.patch.dict(os.environ, {'DATABASE_URI': 'sqlite:///:memory:'})
  def create_app(self):
    test_config = {
        'TESTING': True,
        'PRESERVE_CONTEXT_ON_EXCEPTION': False,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    }
    test_app = app.create_app(test_config)
    return test_app

  def setUp(self):
    super().setUp()
    # Creates tables & loads seed data
    extensions.db.create_all()
    database.load_fixtures()

  def tearDown(self):
    # Ensures next test is in a clean state
    extensions.db.drop_all()
    super().tearDown()
