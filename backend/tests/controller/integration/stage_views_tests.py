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

from absl.testing import absltest

from controller import models
from tests import controller_utils


class TestStageViews(controller_utils.ControllerAppTest):

  def test_list_stages(self):
    response = self.client.get('/api/stages')
    self.assertEqual(response.status_code, 200)

  def test_create_new_stage(self):
    self.assertEmpty(models.Stage.all())
    response = self.client.post('/api/stages')
    self.assertEqual(response.status_code, 201)
    self.assertLen(models.Stage.all(), 1)

  def test_missing_stage(self):
    response = self.client.get('/api/stages/1')
    self.assertEqual(response.status_code, 404)

  def test_retrieve_stage(self):
    models.Stage.create()
    response = self.client.get('/api/stages/1')
    self.assertEqual(response.status_code, 200)

  def test_delete_stage(self):
    models.Stage.create()
    response = self.client.delete('/api/stages/1')
    self.assertEqual(response.status_code, 204)
    self.assertEmpty(models.Stage.all())


if __name__ == '__main__':
  absltest.main()
