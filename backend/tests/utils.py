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

"""Testing utils."""

from unittest import mock

from absl.testing import parameterized

from common import crmint_logging
from common import insight
from common import task
from controller import app
from controller import database
from controller import extensions


class TestConfig(object):
  """Test configuration."""
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class AppTestCase(parameterized.TestCase):
  """Base class for app testing."""

  ctx = None
  client = None

  def create_app(self):
    raise NotImplementedError

  def setUp(self):
    super().setUp()
    test_app = self.create_app()
    # Pushes an application context manually.
    self.ctx = test_app.app_context()
    self.ctx.push()
    # Creates tables & loads seed data
    extensions.db.create_all()
    database.load_fixtures()
    self.client = test_app.test_client()
    self.patched_task_enqueue = self.enter_context(
        mock.patch.object(task.Task, 'enqueue', autospec=True))
    self.patched_log_message = self.enter_context(
        mock.patch.object(crmint_logging, 'log_message', autospec=True))
    self.patched_task_enqueue = self.enter_context(
        mock.patch.object(insight.GAProvider, 'track_event', autospec=True))

  def tearDown(self):
    super().tearDown()
    # Ensures next test is in a clean state
    extensions.db.session.remove()
    extensions.db.drop_all()
    # Drop the app context
    self.ctx.pop()


class ControllerAppTest(AppTestCase):

  def create_app(self):
    test_app = app.create_app(config_object=TestConfig)
    test_app.config['TESTING'] = True
    test_app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    return test_app
