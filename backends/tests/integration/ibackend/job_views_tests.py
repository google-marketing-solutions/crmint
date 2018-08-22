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

from core import models

from tests import utils

class TestJobList(utils.IBackendBaseTest):
  def setUp(self):
    super(TestJobList, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_memcache_stub()

  def test_list_with_success(self):
    pipeline = models.Pipeline.create()
    response = self.client.get('/api/jobs?pipeline_id=%d' % pipeline.id)
    self.assertEqual(response.status_code, 200)
