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

"""Result class definition."""

from common import message


class Result:
  """Async task result to be reported to and processed by controller."""

  _TOPIC = 'crmint-3-task-finished'

  def __init__(self, task_name, job_id, success, workers_to_enqueue=None):
    self.task_name = task_name
    self.job_id = job_id
    self.success = success
    if workers_to_enqueue is None:
      self.workers_to_enqueue = []
    else:
      self.workers_to_enqueue = workers_to_enqueue

  def report(self):
    data = {
        'task_name': self.task_name,
        'job_id': self.job_id,
        'success': self.success,
        'workers_to_enqueue': self.workers_to_enqueue,
    }
    message.send(data, self._TOPIC)

  @classmethod
  def from_request(cls, request):
    """Creates a task result using data form an inciming Flask HTTP request."""
    data = message.extract_data(request)
    return cls(
        data['task_name'],
        data['job_id'],
        data['success'],
        data['workers_to_enqueue'])
