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
from absl.testing import parameterized
from google.appengine.api import mail

from common import crmint_logging
from controller import mailers
from controller import models
from tests import controller_utils


class TestNotificationMailer(controller_utils.ModelTestCase):

  def setUp(self):
    super().setUp()
    self.mailer = mailers.NotificationMailer()
    self.patched_mail_send = self.enter_context(
        mock.patch.object(mail, 'send_mail', autospec=True))
    self.patched_log_message = self.enter_context(
        mock.patch.object(crmint_logging, 'log_message', autospec=True))

  @parameterized.named_parameters(
      ('Pipeline succeeded', models.Pipeline.STATUS.SUCCEEDED, 'succeeded'),
      ('Pipeline failed', models.Pipeline.STATUS.FAILED, 'failed'),
  )
  def test_mail_sent_for_succeeded(self, pipeline_status, expected_str):
    pipeline = models.Pipeline.create(status=pipeline_status)
    pipeline.assign_attributes(dict(emails_for_notifications='john@lenon.com'))
    self.mailer.finished_pipeline(pipeline)
    self.patched_mail_send.assert_called_once_with(
        sender=mock.ANY, to=['john@lenon.com'], subject=mock.ANY, body=mock.ANY)
    self.assertIn(expected_str,
                  self.patched_mail_send.call_args.kwargs['subject'])


if __name__ == '__main__':
  absltest.main()
