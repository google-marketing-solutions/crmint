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

from controller import models
from controller_app import app
from tests import controller_utils


class TestControllerApp(controller_utils.ControllerAppTest):

  def create_app(self):
    app.config['TESTING'] = True
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app

  def test_empty_root_accessible(self):
    self.assertEmpty(models.Pipeline.all())
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)

  def test_list_root_accessible(self):
    models.Pipeline.create(name='Pipeline Foo')
    self.assertLen(models.Pipeline.all(), 1)
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)

  def test_list_muliple_pipelines(self):
    models.Pipeline.create(name='Pipeline Foo')
    models.Pipeline.create(name='Pipeline Bar')
    self.assertLen(models.Pipeline.all(), 2)
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)
