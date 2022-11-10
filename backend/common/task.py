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

from common import message


class Task:
  """Async task to be completed by a CRMint worker."""

  _TOPIC = 'crmint-3-start-task'

  # pylint: disable=too-many-arguments
  def __init__(self, name, pipeline_id, job_id,
               worker_class, worker_params, general_settings, attempts=1):
    self.name = name
    self.pipeline_id = pipeline_id
    self.job_id = job_id
    self.worker_class = worker_class
    self.worker_params = worker_params
    self.general_settings = general_settings
    self.attempts = attempts
  # pylint: enable=too-many-arguments

  def enqueue(self, delay=0):
    data = {
        'task_name': self.name,
        'pipeline_id': self.pipeline_id,
        'job_id': self.job_id,
        'worker_class': self.worker_class,
        'worker_params': self.worker_params,
        'general_settings': self.general_settings,
        'attempts': self.attempts,
    }
    message.send(data, self._TOPIC, delay=delay)

  def reenqueue(self):
    self.attempts += 1
    self.enqueue()

  @classmethod
  def from_request(cls, request):
    """Creates a task using data form an incoming Flask HTTP request."""
    data = message.extract_data(request)
    return cls(
        data['task_name'],
        data['pipeline_id'],
        data['job_id'],
        data['worker_class'],
        data['worker_params'],
        data['general_settings'],
        attempts=data['attempts'])
