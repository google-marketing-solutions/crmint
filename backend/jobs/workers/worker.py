# Copyright 2020 Google Inc. All rights reserved.
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

"""Module with CRMint's base Worker and WorkerException classes."""


import json
from common import crmint_logging
from google.api_core.retry import Retry

_DEFAULT_MAX_RETRIES = 3


class WorkerException(Exception):  # pylint: disable=too-few-public-methods
  """Worker execution exceptions expected in task handler."""


class Worker:
  """Abstract worker class."""

  # A list describing worker parameters. Each element in the list is a tuple
  # of five elements: 0) parameter's name, 1) parameter's type, 2) True if
  # parameter is required, False otherwise, 3) default value to use when
  # parameter value is missing, and 4) label to show near parameter's field in
  # a web UI. See examples below in worker classes.
  PARAMS = []

  # A list with names of general settings that worker needs as its parameters.
  GLOBAL_SETTINGS = []

  # Maximum number of worker execution attempts.
  MAX_ATTEMPTS = 1

  def __init__(self, params, pipeline_id, job_id):
    self._pipeline_id = pipeline_id
    self._job_id = job_id
    self._params = params
    for p in self.PARAMS:
      try:
        self._params[p[0]]
      except KeyError:
        self._params[p[0]] = p[3]
    self._workers_to_enqueue = []

  @Retry()
  def _log(self, level, message, *substs):
    crmint_logging.logger.log_struct({
        'labels': {
            'pipeline_id': self._pipeline_id,
            'job_id': self._job_id,
            'worker_class': self.__class__.__name__,
        },
        'log_level': level,
        'message': message % substs,
    })

  def log_info(self, message, *substs):
    self._log('INFO', message, *substs)

  def log_warn(self, message, *substs):
    self._log('WARNING', message, *substs)

  def log_error(self, message, *substs):
    self._log('ERROR', message, *substs)

  def execute(self):
    self.log_info('Started with params: %s',
                  json.dumps(self._params, sort_keys=True, indent=2,
                             separators=(', ', ': ')))
    # try:
    #   self._execute()
    # except Exception as e:
    #   raise WorkerException(e) from e
    self._execute()
    self.log_info('Finished successfully')
    return self._workers_to_enqueue

  def _execute(self):
    """Abstract method that does actual worker's job."""

  def _enqueue(self, worker_class, worker_params, delay=0):
    self._workers_to_enqueue.append((worker_class, worker_params, delay))
