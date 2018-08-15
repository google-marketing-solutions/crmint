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

from datetime import datetime
from google.appengine.ext import testbed

from core import models
from mock import patch
from tests import utils

import time
import mock

class TestPipelineList(utils.IBackendBaseTest):

  def setUp(self):  
    super(TestPipelineList, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()
    self.testbed.init_datastore_v3_stub()

  def test_list_success(self):
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)

  def test_again_list_success(self):
    """
    This test ensure that the blueprint registration works with
    multiple tests.
    """
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)

class TestPipelineParallelProcessing(utils.IBackendBaseTest):

  def setUp(self):  
    super(TestPipelineParallelProcessing, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()
    self.taskqueue_stub = self.testbed.get_stub(
            testbed.TASKQUEUE_SERVICE_NAME)
    self.taskqueue_stub.StartBackgroundExecution()

  @patch('time.sleep', return_value=None)
  def test_pipeline_success_no_dependencies_jobs(self, patched_time_sleep):
    """
    This test ensures that the pipeline status is updated ('succeeded') 
    after the successful execution (in parallel) of all the jobs.
    """
    pipeline = models.Pipeline.create()
    jobs = [models.Job.create(name=str(index), pipeline_id=pipeline.id, worker_class="WaitingWorker") 
                for index in range(10)]

    params = [
        {'id': None, 'name': 'waiting_time', 'type': 'number', 'value': '5'}
    ]
    relations = {'start_conditions': [], 'params': params}

    for job in jobs:
      job.save_relations(relations)

    self.assertEqual(len(pipeline.jobs.all()), 10)
    
    # necessary for starting the tasks in the background    
    self.taskqueue_stub._auto_task_running = True

    pipeline.start()

    self.taskqueue_stub.StartBackgroundExecution()

    patched_time_sleep(55)

    result = pipeline.job_finished()
    self.assertTrue(result)
    self.assertEqual(pipeline.status, 'succeeded')