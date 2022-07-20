"""Tests for common.message."""

from unittest import mock

from absl.testing import absltest
from google import auth
from google.cloud import pubsub_v1

from common import message


def _make_credentials():
  return mock.create_autospec(
      auth.credentials.Credentials, instance=True, spec_set=True)


class CommonMessageTest(absltest.TestCase):

  def test_send_message_do_not_fail_silently(self):
    """Ensures that we don't silently fail when PubSub fails."""
    mock_future = pubsub_v1.publisher.futures.Future()
    mock_future.set_exception(TimeoutError())
    self.enter_context(
        mock.patch.object(
            pubsub_v1.PublisherClient,
            'publish',
            autospec=True,
            return_value=mock_future))
    self.enter_context(
        mock.patch.object(
            auth,
            'default',
            autospec=True,
            return_value=[_make_credentials, 'PROJECT']))
    with self.assertRaises(TimeoutError):
      message.send(data={'foo': 'bar'}, topic='TOPIC', delay=1)


if __name__ == '__main__':
  absltest.main()
