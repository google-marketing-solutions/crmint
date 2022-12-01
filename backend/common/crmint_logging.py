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

"""Logging helpers."""

import functools
from typing import Optional

from google.auth import credentials as auth_credentials
from google.cloud import logging
from google.cloud.logging import Logger

from controller import shared


@functools.cache
def get_logger(
    *,
    project: Optional[str] = None,
    credentials: Optional[auth_credentials.Credentials] = None) -> Logger:
  """Helper to create and cache a CRMint logger.

  Args:
    project: GCP Project ID string or None.
    credentials: Instance of `google.auth.credentials.Credentials` or None.

  Returns:
    Configured `google.cloud.logging.logger.Logger` instance.
  """
  client = logging.Client(project=project, credentials=credentials)
  return client.logger('crmint-logger')


def log_global_message(message: str, *, log_level: str) -> None:
  """Logs a text message with the given severity level.

  Args:
    message: Message to be logged.
    log_level: Level of logging (e.g. 'INFO', 'ERROR').
  """
  logger = get_logger()
  logger.log_text(message, severity=log_level)


def log_message(
    message: str,
    *,
    log_level: str,
    worker_class: str,
    pipeline_id: int,
    job_id: int,
    logger_project: Optional[str] = None,
    logger_credentials: Optional[auth_credentials.Credentials] = None) -> None:
  """Logs a structured message attached to a given worker, pipeline and job.

  Args:
    message: Message to be logged.
    log_level: Level of logging (e.g. 'INFO', 'ERROR').
    worker_class: Name of the worker class to attach the message to.
    pipeline_id: Id of the pipeline to attach the message to.
    job_id: Id of the job to attach the message to.
    logger_project: GCP Project ID string or None.
    logger_credentials: Instance of `google.auth.credentials.Credentials`
      or None.
  """
  logger = get_logger(project=logger_project, credentials=logger_credentials)
  logger.log_struct({
      'labels': {
          'pipeline_id': pipeline_id,
          'job_id': job_id,
          'worker_class': worker_class,
      },
      'log_level': log_level,
      'message': message,
  })


def log_pipeline_status(
    message: str,
    *,
    pipeline_status: shared.PipelineStatus,
    pipeline_id: int,
    logger_project: Optional[str] = None,
    logger_credentials: Optional[auth_credentials.Credentials] = None) -> None:
  """Logs a structured message attached to a pipeline status change.

  Args:
    message: Message to be logged.
    status: Pipeline status (e.g. 'failed', 'succeeded').
    pipeline_id: Id of the pipeline to attach the message to.
    logger_project: GCP Project ID string or None.
    logger_credentials: Instance of `google.auth.credentials.Credentials`
      or None.
  """
  logger = get_logger(project=logger_project, credentials=logger_credentials)
  logger.log_struct({
      'labels': {
          'pipeline_status': pipeline_status,
          'pipeline_id': pipeline_id,
      },
      'log_type': 'PIPELINE_STATUS',
      'log_level': 'INFO',
      'message': message,
  })
