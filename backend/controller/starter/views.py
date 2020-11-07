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

"""Task results handler."""

import time
from croniter import croniter
from flask import Blueprint, request
from flask_restful import Resource
from common import insight
from common.message import BadRequestError, extract_data
from controller.models import Pipeline
from controller.extensions import api


blueprint = Blueprint('starter', __name__)


class StarterResource(Resource):  # pylint: disable=too-few-public-methods
  """Processes PubSub POST requests from crmint-start-pipeline topic."""

  def _its_time(self, cron_format):
    """Returns True if current time matches cron time spec."""
    now = int(time.time())
    itr = croniter(cron_format, now - 60)
    nxt = itr.get_next()
    return now / 60 * 60 == nxt

  def _start_scheduled_pipelines(self):
    """Finds and tries starting the pipelines scheduled to be executed now."""
    for pipeline in Pipeline.where(run_on_schedule=True).all():
      for schedule in pipeline.schedules:
        if self._its_time(schedule.cron):
          pipeline.start()
          tracker = insight.GAProvider()
          tracker.track_event(category='pipelines', action='scheduled_run')
          break

  def _start_pipelines(self, pipeline_ids):
    """Tries finding and starting pipelines with IDs specified."""
    for pipeline_id in pipeline_ids:
      pipeline = Pipeline.find(pipeline_id)
      if pipeline is not None:
        pipeline.start()
        tracker = insight.GAProvider()
        tracker.track_event(category='pipelines', action='pubsub_run')

  def post(self):
    try:
      data = extract_data(request)
      try:
        pipeline_ids = data['pipeline_ids']
      except KeyError as e:
        raise BadRequestError() from e
      if pipeline_ids == 'scheduled':
        self._start_scheduled_pipelines()
      elif isinstance(pipeline_ids, list):
        self._start_pipelines(pipeline_ids)
      else:
        raise BadRequestError()
    except BadRequestError as e:
      return e.message, e.code
    return 'OK', 200


api.add_resource(StarterResource, '/push/start-pipeline')
