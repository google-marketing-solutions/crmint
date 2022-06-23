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
import json
import os

from google.cloud import pubsub_v1


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


class _Publisher:  # pylint: disable=too-few-public-methods
  """Singleton for publishing PubSub messages using a persistent client."""

  _PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
  _client = None

  @classmethod
  def publish(cls, topic, data, delay):
    if cls._client is None:
      cls._client = pubsub_v1.PublisherClient()
    topic_path = f'projects/{cls._PROJECT}/topics/{topic}'
    binary_data = json.dumps(data).encode('utf-8')
    delay_delta = datetime.timedelta(seconds=delay)
    start_time = int((datetime.datetime.utcnow() + delay_delta).timestamp())
    cls._client.publish(topic_path, binary_data, start_time=str(start_time))


def send(data, topic, delay=0):
  """Sends data in a message to a PubSub topic to be processed with a delay."""
  _Publisher.publish(topic, data, delay)


def extract_data(request):  # pylint: disable=unused-argument
  """Gets a PubSub message data from an incoming Flask request."""
  # envelope = json.loads(request.data.decode('utf-8'))
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
