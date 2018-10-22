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

"""Tracking package."""
import requests

TRACKER = None

def init_tracking(enabled=True):
  global TRACKER
  if enabled:
    TRACKER = GATracker()
  else:
    TRACKER = EmptyTracker()


class EmptyTrackingIDException(Exception):
  """
  Exception for the required MP parameter tid
  """
  pass


class EmptyTracker(object):
  """Abstract tracking class."""
  URL = "https://www.google-analytics.com/collect"

  def __init__(self, tracking_id=None, client_id="555"):
    self.tid = tracking_id
    self.client_id = client_id

  def send_request(self, data):
    requests.post(self.URL, data)

  def track_run_pipeline(self):
    pass



class GATracker(EmptyTracker):

  def __init__(self, tracking_id=None, client_id="555"):
    if not tracking_id:
      raise EmptyTrackingIDException("TrackingId for GATracker not set")
    EmptyTracker.__init__(self, tracking_id, client_id)

  def track_run_pipeline(self):
    data = {
        "v": 1,
        "tid": self.tid,
        "cid": self.client_id,
        "t": "event",
        "ec": "pipeline",
        "ea": "run"
        }
    self.send_request(data)
