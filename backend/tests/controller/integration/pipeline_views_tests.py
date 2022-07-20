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

from unittest import mock

from absl.testing import absltest

from common import crmint_logging
from controller import models
from tests import controller_utils


class TestPipelineViews(controller_utils.ControllerAppTest):

  def test_empty_list(self):
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)

  def test_list_with_one_pipeline(self):
    """Ensures that the blueprint registration works with multiple tests."""
    models.Pipeline.create()
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)

  def test_missing_pipeline(self):
    response = self.client.get('/api/pipelines/1')
    self.assertEqual(response.status_code, 404)

  def test_retrieve_pipeline(self):
    pipeline = models.Pipeline.create()
    models.Job.create(pipeline_id=pipeline.id)
    response = self.client.get('/api/pipelines/1')
    self.assertEqual(response.status_code, 200)

  def test_start_pipeline(self):
    pipeline = models.Pipeline.create()
    models.Job.create(pipeline_id=pipeline.id)
    response = self.client.post('/api/pipelines/1/start')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(pipeline.status, models.Job.STATUS.RUNNING)

  def test_stop_pipeline(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.RUNNING)
    response = self.client.post('/api/pipelines/1/stop')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(pipeline.status, models.Job.STATUS.STOPPING)

  def test_export_pipeline(self):
    pipeline = models.Pipeline.create(name='My Pipeline')
    models.Job.create(pipeline_id=pipeline.id)
    response = self.client.get('/api/pipelines/1/export')
    self.assertEqual(response.status_code, 200)

  def test_enable_run_on_schedule(self):
    pipeline = models.Pipeline.create()
    response = self.client.patch(
        '/api/pipelines/1/run_on_schedule?run_on_schedule=True')
    self.assertEqual(response.status_code, 200)
    self.assertTrue(pipeline.run_on_schedule)

  def test_disable_run_on_schedule(self):
    pipeline = models.Pipeline.create()
    response = self.client.patch(
        '/api/pipelines/1/run_on_schedule?run_on_schedule=False')
    self.assertEqual(response.status_code, 200)
    self.assertFalse(pipeline.run_on_schedule)

  def test_retrieve_logs(self):
    self.enter_context(
        mock.patch.object(crmint_logging, 'get_logger', autospec=True))
    models.Pipeline.create()
    response = self.client.get('/api/pipelines/1/logs')
    self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
  absltest.main()
