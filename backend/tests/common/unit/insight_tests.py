"""Tests for common.insight."""

import json
import os
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from common import insight
from tests import utils


class CommonInsightOnFreshInstallTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    # `create_tempfile` needs access to --test_tmpdir, however in the OSS world
    # pytest doesn't run `absltest.main`, so we need to init flags ourselves.
    utils.initialize_flags_with_defaults()
    # Overrides the default data directory with a custom temporary directory.
    tmp_data_dir = self.create_tempdir('data_dir')
    tmp_filepath = os.path.join(tmp_data_dir, 'insight.json')
    self.enter_context(
        mock.patch.object(insight, 'INSIGHT_CONF_FILEPATH', tmp_filepath))

  def test_client_id_defaults_to_none(self):
    tracker = insight.GAProvider()
    self.assertIsNone(tracker.client_id)

  def test_can_assign_new_client_id(self):
    tracker = insight.GAProvider(allow_new_client_id=True)
    self.assertIsNotNone(tracker.client_id)

  def test_sending_event(self):
    tracker = insight.GAProvider(allow_new_client_id=True)
    patched_send = self.enter_context(
        mock.patch.object(tracker, '_send', autospec=True))
    tracker.track('some_event')
    patched_send.assert_called_once_with(
        {'type': 'pageview', 'path': '/some_event'})


class CommonInsightWithConsentTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    # `create_tempfile` needs access to --test_tmpdir, however in the OSS world
    # pytest doesn't run `absltest.main`, so we need to init flags ourselves.
    utils.initialize_flags_with_defaults()
    # Overrides the default data directory with a custom temporary directory.
    content = json.dumps({'client_id': 123, 'opt_out': False})
    tmp_filepath = self.create_tempfile('insight.json', content)
    self.enter_context(
        mock.patch.object(insight, 'INSIGHT_CONF_FILEPATH', tmp_filepath))

  def test_expose_opt_out(self):
    tracker = insight.GAProvider()
    self.assertFalse(tracker.opt_out)

  def test_send_event(self):
    tracker = insight.GAProvider(allow_new_client_id=True)
    patched_send = self.enter_context(
        mock.patch.object(tracker, '_send', autospec=True))
    tracker.track('some_event')
    patched_send.assert_called_once_with(
        {'type': 'pageview', 'path': '/some_event'})


class CommonInsightNoConsentTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    # `create_tempfile` needs access to --test_tmpdir, however in the OSS world
    # pytest doesn't run `absltest.main`, so we need to init flags ourselves.
    utils.initialize_flags_with_defaults()
    # Overrides the default data directory with a custom temporary directory.
    content = json.dumps({'client_id': 123, 'opt_out': True})
    tmp_filepath = self.create_tempfile('insight.json', content)
    self.enter_context(
        mock.patch.object(insight, 'INSIGHT_CONF_FILEPATH', tmp_filepath))

  def test_not_raising_exception_when_loading_file(self):
    tracker = insight.GAProvider()
    self.assertEqual(tracker.client_id, 123)

  def test_reuse_client_id(self):
    tracker = insight.GAProvider(allow_new_client_id=True)
    self.assertEqual(tracker.client_id, 123)

  def test_expose_opt_out(self):
    tracker = insight.GAProvider()
    self.assertTrue(tracker.opt_out)

  def test_not_sending_event(self):
    self.patched_send = self.enter_context(
        mock.patch.object(insight.GAProvider, '_send', autospec=True))
    tracker = insight.GAProvider()
    tracker.track('some_event')
    self.patched_send.assert_not_called()


class CommonInsightFromEnvTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    # `create_tempfile` needs access to --test_tmpdir, however in the OSS world
    # pytest doesn't run `absltest.main`, so we need to init flags ourselves.
    utils.initialize_flags_with_defaults()
    # Overrides the default data directory with a custom temporary directory.
    tmp_data_dir = self.create_tempdir('data_dir')
    tmp_filepath = os.path.join(tmp_data_dir, 'insight.json')
    self.enter_context(
        mock.patch.object(insight, 'INSIGHT_CONF_FILEPATH', tmp_filepath))

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
