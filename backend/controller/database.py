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

"""Database helper methods."""

from typing import Callable, Optional

import flask
from sqlalchemy import orm

from common import crmint_logging
from controller import extensions
from controller import models


def load_fixtures(logger_func: Optional[Callable[[str], None]] = None) -> None:
  """Loads initial data into the database.

  Args:
    logger_func: Logger function to display the loading state.
  """
  general_settings = [
      'client_id', 'client_secret',
      'google_ads_authentication_code', 'google_ads_refresh_token',
      'developer_token', 'app_conversion_api_developer_token']
  for setting in general_settings:
    general_setting = models.GeneralSetting.where(name=setting).first()
    if not general_setting:
      general_setting = models.GeneralSetting()
      general_setting.name = setting
      general_setting.save()
      if logger_func:
        logger_func('Added setting %s' % setting)


def reset_jobs_and_pipelines_statuses_to_idle() -> None:
  models.TaskEnqueued.query.delete()
  for pipeline in models.Pipeline.all():
    for job in pipeline.jobs:
      job.update(status='idle')
    pipeline.update(status='idle')


def shutdown(app: flask.Flask) -> None:
  """Cleans database state."""
  # Find all Sessions in memory and close them.
  orm.close_all_sessions()
  crmint_logging.log_global_message(
      'All sessions closed.', log_level='WARNING')
  # Each connection was released on execution, so just formally
  # dispose of the db connection if it's been instantiated
  extensions.db.get_engine(app).dispose()
  crmint_logging.log_global_message(
      'Database connection disposed.', log_level='WARNING')
