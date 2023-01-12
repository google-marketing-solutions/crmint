"""Tests for common.insight."""

import json
import os
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from common import insight
from tests import utils


class CommonInsightFromEnvTest(absltest.TestCase):

  @mock.patch.dict(os.environ, {'REPORT_USAGE_ID': '123456'})
  def test_consent(self):
    tracker = insight.GAProvider()
    self.assertFalse(tracker.opt_out)
    self.assertEqual(tracker.client_id, '123456')

  @mock.patch.dict(os.environ, {'REPORT_USAGE_ID': '123456'})
  def test_send_event_with_consent(self):
    tracker = insight.GAProvider()
    patched_send = self.enter_context(
        mock.patch.object(tracker, '_send', autospec=True))
    tracker.track('some_event')
    patched_send.assert_called_once_with(
        {'type': 'pageview', 'path': '/some_event'})

  @mock.patch.dict(os.environ, {'REPORT_USAGE_ID': ''})
  def test_optout(self):
    tracker = insight.GAProvider()
    self.assertTrue(tracker.opt_out)
    self.assertEqual(tracker.client_id, '')

  @mock.patch.dict(os.environ, {'REPORT_USAGE_ID': ''})
  def test_do_not_send_event_without_consent(self):
    tracker = insight.GAProvider()
    patched_send = self.enter_context(
        mock.patch.object(tracker, '_send', autospec=True))
    tracker.track('some_event')
    patched_send.assert_not_called()


if __name__ == '__main__':
  absltest.main()
