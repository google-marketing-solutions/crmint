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

from typing import Optional

from google.auth import credentials as auth_credentials
from google.cloud import logging
from google.cloud.logging import Logger


def get_logger(
    *,
    project: Optional[str] = None,
    credentials: Optional[auth_credentials.Credentials] = None) -> Logger:
  """Helper to create a CRMint logger.

  Args:
    project: GCP Project ID string or None.
    credentials: Instance of `google.auth.credentials.Credentials` or None.

  Returns:
    Configured `google.cloud.logging.logger.Logger` instance.
  """
  client = logging.Client(project=project, credentials=credentials)
  return client.logger('crmint-logger')
