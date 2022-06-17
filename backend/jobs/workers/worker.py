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
from typing import Any, Optional

from google.api_core.retry import Retry
from google.auth import credentials

from common import crmint_logging

_DEFAULT_MAX_RETRIES = 3


# TODO(dulacp): Change this exception name to `WorkerError`
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

  def __init__(self,
               params: dict[str, Any],
               pipeline_id: int,
               job_id: int,
               logger_project: Optional[str] = None,
               logger_credentials: Optional[credentials.Credentials] = None):
    """Create an instance of Worker.

    Args:
      params: Dictionary of parameters for the worker.
      pipeline_id: Integer representing the pipeline id in the database.
      job_id: Integer representing the job id in the database.
      logger_project: String representing the GCP Project ID.
      logger_credentials: Credentials for the logging client.
    """
    self._pipeline_id = pipeline_id
    self._job_id = job_id
    self._params = params
    for p in self.PARAMS:
      try:
        self._params[p[0]]
      except KeyError:
        self._params[p[0]] = p[3]
    self._workers_to_enqueue = []
    # TODO(dulacp): remove these parameters, mock `crmint_logging.log_message`
    self._logger_project = logger_project
    self._logger_credentials = logger_credentials

  @Retry()
  def _log(self, level: str, message: str) -> None:
    crmint_logging.log_message(
        message,
        log_level=level,
        pipeline_id=self._pipeline_id,
        job_id=self._job_id,
        worker_class=self.__class__.__name__,
        logger_project=self._logger_project,
        logger_credentials=self._logger_credentials)

  def log_info(self, message: str) -> None:
    """Logs a message at the INFO level.

    Args:
      message: String containg the message to log.
    """
    self._log('INFO', message)

  def log_warn(self, message: str) -> None:
    """Logs a message at the WARNING level.

    Args:
      message: String containg the message to log.
    """
    self._log('WARNING', message)

  def log_error(self, message: str) -> None:
    """Logs a message at the ERROR level.

    Args:
      message: String containg the message to log.
    """
    self._log('ERROR', message)

  def execute(self):
    """Wrapper around the `_execute` method, logging valuable informations."""
    format_separators = (', ', ': ')
    formatted_params = json.dumps(
        self._params, sort_keys=True, indent=2, separators=format_separators)
    self.log_info(f'Started with params: {formatted_params}')
    self._execute()
    self.log_info('Finished successfully')
    return self._workers_to_enqueue

  def _execute(self):
    """Abstract method that does actual worker's job."""
    raise NotImplementedError

  def _enqueue(self, worker_class, worker_params, delay=0):
    self._workers_to_enqueue.append((worker_class, worker_params, delay))
