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

from core import mailers
from core import models

import os
import sys
sys.path.insert(0, os.getcwd())
from tests import utils


class TestNotificationMailer(utils.ModelTestCase):

  def setUp(self):
    super(TestNotificationMailer, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_mail_stub()
    self.mailer = mailers.NotificationMailer()
    self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)

  def tearDown(self):
    super(TestNotificationMailer, self).tearDown()
    self.testbed.deactivate()

  def test_mail_has_been_sent(self):
    pipeline = models.Pipeline()
    pipeline.assign_attributes(dict(emails_for_notifications='john@lenon.com'))
    self.mailer.finished_pipeline(pipeline)
    messages = self.mail_stub.get_sent_messages(to='john@lenon.com')
    self.assertEqual(1, len(messages))
    self.assertEqual('john@lenon.com', messages[0].to)
