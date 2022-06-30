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

"""Mailer implementation."""

from google.appengine.api import mail

from controller import app_data


class BaseNotifier(object):
  """Base class for notifier implementations."""
  __abstract__ = True

  def recipients(self, other_recipients):
    from controller import models  # pylint: disable=g-import-not-at-top
    gsetting = models.GeneralSetting.where(
        name='emails_for_notifications').first()
    if gsetting is None or gsetting.value is None:
      recipients = other_recipients
    else:
      recipients = list(set(gsetting.value.split() + other_recipients))
    return recipients


class NotificationMailer(BaseNotifier):
  """Mails the notification to the end user."""

  SENDER = 'CRMintApp %s Notification <%s>' % (
      app_data.APP_DATA['app_title'],
      app_data.APP_DATA['notification_sender_email']
  )

  def finished_pipeline(self, pipeline: 'models.Pipeline') -> None:
    """Sends a mail with the pipeline status.

    Args:
      pipeline: Instance of the pipeline which just finished its execution.
    """
    recipients = self.recipients(pipeline.recipients)
    if recipients:
      subject = f'Pipeline {pipeline.name} {pipeline.status}'
      mail.send_mail(sender=self.SENDER,
                     to=recipients,
                     subject=subject,
                     body=subject)
