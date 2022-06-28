# Copyright 2020 Google Inc
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

"""Helpers for communicating with Pub/Sub."""

import base64
import datetime
import functools
import json
import os
from typing import Any

import flask
from google.cloud import pubsub_v1

from common import crmint_logging

_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
_PUBSUB_TIMEOUT = 10  # Unit in seconds.


class _Error(Exception):
  """Generic message module error."""

  def __init__(self, message, code):
    super().__init__(message, code)
    self.message = message
    self.code = code


class TooEarlyError(_Error):
  """Exception to be raised when it's too eraly to process a delayed message."""

  def __init__(self, scheduled_time):
    message = f'Resend message after {scheduled_time}'
    super().__init__(message, 419)


class BadRequestError(_Error):
  """Exception to be raised if there is no valid message in a request."""

  def __init__(self):
    super().__init__('There is no valid PubSub message in the request', 400)


@functools.cache
def _get_publisher_client() -> pubsub_v1.PublisherClient:
  return pubsub_v1.PublisherClient()


def send(data: dict[str, Any], topic: str, delay: int = 0) -> None:
  """Sends data in a message to a PubSub topic to be processed with a delay.

  Args:
    data: Data structure to encode as the message.
    topic: Name of the topic to publish messages to.
    delay: Number of seconds to delay the delivery of the message.
      Defaults to zero.

  Raises:
    pubsub_v1.exceptions.TimeoutError: if the message to Pub/Sub times out.
    Exception: for undefined exceptions in the underlying pubsub call execution.
  """
  topic_path = f'projects/{_PROJECT}/topics/{topic}'
  binary_data = json.dumps(data).encode('utf-8')
  delay_delta = datetime.timedelta(seconds=delay)
  start_time = int((datetime.datetime.utcnow() + delay_delta).timestamp())
  client = _get_publisher_client()
  future = client.publish(topic_path,
                          binary_data,
                          start_time=str(start_time))
  future.result(timeout=_PUBSUB_TIMEOUT)


def extract_data(request: flask.Request) -> dict[str, Any]:
  """Returns a PubSub message data from an incoming Flask request.

  Args:
    request: Incoming Flask request.
  """
  envelope = request.get_json()
  try:
    message = envelope['message']
  except (TypeError, KeyError) as e:
    raise BadRequestError() from e
  try:
    start_time = datetime.datetime.fromtimestamp(
        int(message['attributes']['start_time']))
    if datetime.datetime.utcnow() < start_time:
      raise TooEarlyError(start_time)
  except KeyError as e:
    raise BadRequestError() from e
  try:
    data = json.loads(base64.b64decode(message['data']).decode('utf-8'))
  except (
      KeyError,
      base64.binascii.Error,
      UnicodeDecodeError,
      json.decoder.JSONDecodeError) as e:
    raise BadRequestError() from e
  return data


def shutdown() -> None:
  """Cleans Pub/Sub client state."""
  # Stop accepting new messages and commit outstanding ones (if possible).
  _get_publisher_client().stop()
  crmint_logging.log_global_message(
      'PubSub client stopped.', log_level='WARNING')
