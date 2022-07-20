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

from jobs_app import app
from tests import utils


class TestJobsApp(utils.AppTestCase):

  def create_app(self):
    app.config['TESTING'] = True
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

  def test_root_accessible(self):
    response = self.client.get('/api/workers')
    self.assertEqual(response.status_code, 200)
