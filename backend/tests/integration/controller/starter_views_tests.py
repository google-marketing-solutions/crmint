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

import base64
import json
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
import flask_restful
import freezegun

from common import crmint_logging
from common import insight
from common import task
from controller import app
from controller import database
from controller import extensions
from controller import models


class TestConfig(object):
  """Test configuration."""
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# TODO(dulacp): remove these from the global scope by resetting API resources.
test_app = app.create_app(config_object=TestConfig)
extensions.db.init_app(test_app)


class AppTestCase(parameterized.TestCase):

  def setUp(self):
    super().setUp()
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


class TestStarterViews(AppTestCase):

  @freezegun.freeze_time('2015-06-18T16:07:19')
  def test_can_start_single_pipeline(self):
    pipeline = models.Pipeline.create()
    models.Job.create(pipeline_id=pipeline.id)
    data = {
        'pipeline_ids': [pipeline.id],
    }
    data_encoded = base64.b64encode(json.dumps(data).encode('utf8'))
    payload = {
        'message': {
            'attributes': {
                'start_time': 1434636430,  # 9 seconds ago
            },
            'data': data_encoded.decode('utf8'),
        }
    }
    response = self.client.post('/push/start-pipeline', json=payload)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)

  @parameterized.named_parameters(
      ('Before schedule', '6 16 * * *', models.Pipeline.STATUS.IDLE),
      ('On schedule', '7 16 * * *', models.Pipeline.STATUS.RUNNING),
      ('After schedule', '8 16 * * *', models.Pipeline.STATUS.IDLE),
  )
  @freezegun.freeze_time('2015-06-18T16:07:19')
  def test_can_start_pipeline_on_schedule(self, cron, pipeline_status):
    pipeline = models.Pipeline.create(run_on_schedule=True)
    models.Job.create(pipeline_id=pipeline.id)
    models.Schedule.create(pipeline_id=pipeline.id, cron=cron)
    data = {
        'pipeline_ids': 'scheduled',
    }
    data_encoded = base64.b64encode(json.dumps(data).encode('utf8'))
    payload = {
        'message': {
            'attributes': {
                'start_time': 1434636430,  # 9 seconds ago
            },
            'data': data_encoded.decode('utf8'),
        }
    }
    response = self.client.post('/push/start-pipeline', json=payload)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(pipeline.status, pipeline_status)


if __name__ == '__main__':
  absltest.main()
