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

from google.appengine.ext import testbed
import mock

from core import models

import os
import sys
sys.path.insert(0, os.getcwd())
from tests import utils


class TestTaskCreation(utils.JBackendBaseTest):

  def setUp(self):
    super(TestTaskCreation, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestTaskCreation, self).tearDown()
    self.testbed.deactivate()

  def test_get_helloword(self):
    response = self.client.get('/hello')
    self.assertEqual(response.status_code, 200)

  @mock.patch('core.cloud_logging.logger')
  def test_submit_task_success(self, patched_logger):
    # NB: patching the StackDriver logger is needed because there is no
    #     testbed service available for now
    patched_logger.log_struct.__name__ = 'foo'
    patched_logger.log_struct.return_value = 'patched_log_struct'
    pipeline = models.Pipeline.create()
    job = models.Job.create(pipeline_id=pipeline.id)
    self.assertTrue(job.get_ready())
    task = job.start()
    self.assertIsNotNone(task)
    data = dict(
        job_id=job.id,
        worker_class='Commenter',
        worker_params='{"comment": "", "success": false}',
        task_name=task.name)
    headers = {
        'X-AppEngine-TaskExecutionCount': '0'}
    response = self.client.post('/task', headers=headers, data=data)
    self.assertEqual(response.status_code, 200)
