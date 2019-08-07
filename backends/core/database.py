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

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy_mixins import AllFeaturesMixin, ReprMixin

from core.mixins import TimestampsMixin

engine = None
Base = declarative_base()


class BaseModel(Base, AllFeaturesMixin, TimestampsMixin):
  """Base class for models"""
  __abstract__ = True
  __repr__ = ReprMixin.__repr__


def init_engine(uri, **kwargs):
  """Initialization db engine"""
  global engine
  engine = create_engine(uri, **kwargs)
  session = scoped_session(sessionmaker(bind=engine, autocommit=True))
  BaseModel.set_session(session)
  return engine


def init_db():
  """Create model tables.

  NB: Import all modules here that might define models so that
      they will be registered properly on the metadata.  Otherwise
      you will have to import them first before calling init_db().
  """
  from core import models  # NOQA
  Base.metadata.create_all(bind=engine)


def load_fixtures(logger_func=None):
  """Load initial data into the database

  :param: Logger function to display the loading state
  """
  from core import models
  # added two more rows to list, for google ads auth code and refresh token
  general_settings = ['client_id', 'client_secret', 'emails_for_notifications', 'google_ads_authentication_code', 'google_ads_refresh_token', 'developer_token']
  for setting in general_settings:
    general_setting = models.GeneralSetting.where(name=setting).first()
    if not general_setting:
      general_setting = models.GeneralSetting()
      general_setting.name = setting
      general_setting.save()
      if logger_func:
        logger_func('Added setting %s' % setting)

def reset_jobs_and_pipelines_statuses_to_idle():
  from core.models import Pipeline
  for pipeline in Pipeline.all():
    for job in pipeline.jobs:
      job.update(status='idle')
    pipeline.update(status='idle')
