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

"""Cron handler."""
import logging
import time

from croniter import croniter
from flask import Blueprint
from flask_restful import Resource

from core import insight
from core.models import Pipeline
from jbackend.extensions import api

blueprint = Blueprint('cron', __name__)


class Cron(Resource):
  """Resource to handle GET requests from cron service."""

  def _its_time(self, cron_format):
    """Returns True if current time matches cron time spec."""
    now = int(time.time())
    itr = croniter(cron_format, now - 60)
    nxt = itr.get_next()
    return now / 60 * 60 == nxt

  def get(self):
    """Finds and enqueues pipelines scheduled to be executed now."""
    for pipeline in Pipeline.where(run_on_schedule=True).all():
      logging.info('Checking schedules for pipeline %s', pipeline.name)
      for schedule in pipeline.schedules:
        logging.info('Checking schedule with cron string %s', schedule.cron)
        if self._its_time(schedule.cron):
          logging.info('Trying to start pipeline %s', pipeline.name)
          pipeline.start()
          insight = insight.GAProvider()
          insight.track_event(category='pipelines', action='scheduled_run')
          break
    return 'OK', 200


api.add_resource(Cron, '/cron')
