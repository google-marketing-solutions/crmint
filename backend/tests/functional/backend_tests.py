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

import os
import sys
sys.path.insert(0, os.getcwd())
from tests import utils


class TestBaseBackendEndToEnd(utils.BaseTestCase):

  def _setup_config(self):
    # Setup the config var for MySQL
    # NB: the config.py file is not tracked by the repository, so it's
    #     okay to override its content
    from appengine_config import PROJECT_DIR
    config_path = os.path.join(PROJECT_DIR, 'instance/config.py')
    with open(config_path, 'wb') as f:
      f.write('SQLALCHEMY_DATABASE_URI="mysql+mysqldb://'
              'crmint:crmint@localhost:3306/crmintapp_test"')


class TestIBackend(TestBaseBackendEndToEnd):

  def create_app(self):
    self._setup_config()
    from run_ibackend import app
    app.config['TESTING'] = True
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

  def test_root_accessible(self):
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)


class TestJBackend(TestBaseBackendEndToEnd):

  def create_app(self):
    self._setup_config()
    from run_jbackend import app
    app.config['TESTING'] = True
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

  def test_root_accessible(self):
    response = self.client.get('/hello')
    self.assertEqual(response.status_code, 200)
