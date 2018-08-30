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

"""Pipeline section."""
import time
import datetime
import uuid

from google.appengine.api import app_identity
from google.appengine.api import urlfetch
from google.cloud.logging import DESCENDING

import werkzeug
from flask import Blueprint, json
from flask_restful import abort
from flask_restful import fields
from flask_restful import marshal_with
from flask_restful import Resource
from flask_restful import reqparse

from core import cache
from core import cloud_logging
from core.models import Job
from core.models import Pipeline

from ibackend.extensions import api

blueprint = Blueprint('pipeline', __name__)

parser = reqparse.RequestParser()
parser.add_argument('name')
parser.add_argument('emails_for_notifications')
parser.add_argument('run_on_schedule')
parser.add_argument('schedules', type=list, location='json')
parser.add_argument('params', type=list, location='json')

schedule_fields = {
    'id': fields.Integer,
    'pipeline_id': fields.Integer,
    'cron': fields.String,
}
param_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'type': fields.String,
    'value': fields.Raw(attribute='api_val'),
    'label': fields.String
}
pipeline_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'emails_for_notifications': fields.String,
    'status': fields.String(attribute='state'),
    'updated_at': fields.String,
    'run_on_schedule': fields.Boolean,
    'schedules': fields.List(fields.Nested(schedule_fields)),
    'params': fields.List(fields.Nested(param_fields)),
    'message': fields.String,
    'has_jobs': fields.Boolean,
}


def abort_if_pipeline_doesnt_exist(pipeline, pipeline_id):
  if pipeline is None:
    abort(404, message="Pipeline {} doesn't exist".format(pipeline_id))


class PipelineSingle(Resource):
  """Shows a single pipeline item and lets you delete a pipeline item"""

  @marshal_with(pipeline_fields)
  def get(self, pipeline_id):
    pipeline = Pipeline.find(pipeline_id)
    abort_if_pipeline_doesnt_exist(pipeline, pipeline_id)
    return pipeline

  @marshal_with(pipeline_fields)
  def delete(self, pipeline_id):
    pipeline = Pipeline.find(pipeline_id)

    abort_if_pipeline_doesnt_exist(pipeline, pipeline_id)
    if pipeline.is_blocked():
      return {
          'message': 'Removing of active pipeline is unavailable'
      }, 422

    pipeline.destroy()
    return {}, 204

  @marshal_with(pipeline_fields)
  def put(self, pipeline_id):
    pipeline = Pipeline.find(pipeline_id)
    abort_if_pipeline_doesnt_exist(pipeline, pipeline_id)

    if pipeline.is_blocked():
      return {
          'message': 'Editing of active pipeline is unavailable'
      }, 422

    args = parser.parse_args()

    pipeline.assign_attributes(args)
    pipeline.save()
    pipeline.save_relations(args)
    return pipeline, 200


class PipelineList(Resource):
  """Shows a list of all pipelines, and lets you POST to add new pipelines"""

  @marshal_with(pipeline_fields)
  def get(self):
    pipelines = Pipeline.all()
    return pipelines

  @marshal_with(pipeline_fields)
  def post(self):
    args = parser.parse_args()
    pipeline = Pipeline(name=args['name'])
    pipeline.assign_attributes(args)
    pipeline.save()
    pipeline.save_relations(args)
    return pipeline, 201


class PipelineStart(Resource):
  """Class for run pipeline"""
  @marshal_with(pipeline_fields)
  def post(self, pipeline_id):
    pipeline = Pipeline.find(pipeline_id)
    pipeline.start()
    return pipeline


class PipelineStop(Resource):
  """Class for stopping of pipeline"""

  @marshal_with(pipeline_fields)
  def post(self, pipeline_id):
    pipeline = Pipeline.find(pipeline_id)
    pipeline.stop()
    return pipeline


class PipelineExport(Resource):
  """Class for exporting of pipeline in yaml format"""

  def get(self, pipeline_id):
    pipeline = Pipeline.find(pipeline_id)

    jobs = self.__get_jobs__(pipeline)

    pipeline_params = []
    for param in pipeline.params:
      pipeline_params.append({
          'name': param.name,
          'value': param.value,
          'type': param.type,
      })

    pipeline_schedules = []
    for schedule in pipeline.schedules:
      pipeline_schedules.append({
          'cron': schedule.cron,
      })

    data = {
        'name': pipeline.name,
        'jobs': jobs,
        'params': pipeline_params,
        'schedules': pipeline_schedules
    }

    ts = time.time()
    pipeline_date = datetime.datetime.fromtimestamp(ts)
    pipeline_date_formatted = pipeline_date.strftime('%Y%m%d%H%M%S')
    filename = pipeline.name.lower() + "-" + pipeline_date_formatted + ".json"
    return data, 200, {
        'Access-Control-Expose-Headers': 'Filename',
        'Content-Disposition': "attachment; filename=" + filename,
        'Filename': filename,
        'Content-type': 'text/json'
    }

  def __get_jobs__(self, pipeline):
    job_mapping = {}
    for job in pipeline.jobs:
      job_mapping[job.id] = uuid.uuid4().hex

    jobs = []
    for job in pipeline.jobs:
      params = []
      for param in job.params:
        params.append({
            'name': param.name,
            'value': param.api_val,
            'label': param.label,
            'is_required': param.is_required,
            'type': param.type,
            'description': param.description
        })
      start_conditions = []
      for start_condition in job.start_conditions:
        start_conditions.append({
            'preceding_job_id': job_mapping[start_condition.preceding_job_id],
            'condition': start_condition.condition
        })
      jobs.append({
          'id': job_mapping[job.id],
          'name': job.name,
          'worker_class': job.worker_class,
          'params': params,
          'hash_start_conditions': start_conditions
      })
    return jobs


import_parser = reqparse.RequestParser()
import_parser.add_argument(
    'upload_file',
    type=werkzeug.datastructures.FileStorage,
    location='files'
)


class PipelineImport(Resource):
  """Class for importing of pipeline in yaml format"""

  @marshal_with(pipeline_fields)
  def post(self):
    args = import_parser.parse_args()

    file_ = args['upload_file']
    data = {}
    if file_:
      data = json.loads(file_.read())
      pipeline = Pipeline(name=data['name'])
      pipeline.save()
      pipeline.import_data(data)
      return pipeline, 201

    return data


class PipelineRunOnSchedule(Resource):

  @marshal_with(pipeline_fields)
  def patch(self, pipeline_id):
    pipeline = Pipeline.find(pipeline_id)
    args = parser.parse_args()
    pipeline.update(run_on_schedule=(args['run_on_schedule'] == 'True'))
    return pipeline


log_parser = reqparse.RequestParser()
log_parser.add_argument('next_page_token')
log_parser.add_argument('worker_class')
log_parser.add_argument('job_id')
log_parser.add_argument('log_level')
log_parser.add_argument('query')
log_parser.add_argument('fromdate')
log_parser.add_argument('todate')

log_fields = {
    'timestamp': fields.String,
    'payload': fields.Raw,
    'job_name': fields.String
}

logs_fields = {
    'entries': fields.List(fields.Nested(log_fields)),
    'next_page_token': fields.String
}


class PipelineLogs(Resource):

  def get(self, pipeline_id):
    args = log_parser.parse_args()
    entries = []
    urlfetch.set_default_fetch_deadline(300)

    next_page_token = args.get('next_page_token')
    page_size = 20
    from core import cloud_logging

    project_id = app_identity.get_application_id()
    filter_ = 'logName="projects/%s/logs/%s"' % (project_id, cloud_logging.logger_name)
    filter_ += ' AND jsonPayload.labels.pipeline_id="%s"' % pipeline_id
    if args.get('worker_class'):
      filter_ += ' AND jsonPayload.labels.worker_class="%s"' \
          % args.get('worker_class')
    if args.get('job_id'):
      filter_ += ' AND jsonPayload.labels.job_id="%s"' % args.get('job_id')
    if args.get('log_level'):
      filter_ += ' AND jsonPayload.log_level="%s"' % args.get('log_level')
    if args.get('query'):
      filter_ += ' AND jsonPayload.message:"%s"' % args.get('query')
    if args.get('fromdate'):
      filter_ += ' AND timestamp>="%s"' % args.get('fromdate')
    if args.get('todate'):
      filter_ += ' AND timestamp<="%s"' % args.get('todate')
    iterator = cloud_logging.client.list_entries(
        projects=[project_id],
        filter_=filter_,
        order_by=DESCENDING,
        page_size=page_size,
        page_token=next_page_token
    )
    page = next(iterator.pages)

    for entry in page:
      # print '    Page number: %d' % (iterator.page_number,)
      # print '  Items in page: %d' % (page.num_items,)
      # print 'Items remaining: %d' % (page.remaining,)
      # print 'Next page token: %s' % (iterator.next_page_token,)
      # print '----------------------------'
      if isinstance(entry.payload, dict) \
         and entry.payload.get('labels') \
         and entry.payload.get('labels').get('job_id'):

        job = Job.find(entry.payload.get('labels').get('job_id'))
        if job:
          log = {
              'timestamp': entry.timestamp.__str__(),
              'payload': entry.payload,
              'job_name': job.name,
              'log_level': entry.payload.get('log_level', 'INFO')
          }
          entries.append(log)
      next_page_token = iterator.next_page_token
    return {
        'entries': entries,
        'next_page_token': next_page_token
    }


api.add_resource(PipelineList, '/pipelines')
api.add_resource(PipelineSingle, '/pipelines/<pipeline_id>')
api.add_resource(PipelineStart, '/pipelines/<pipeline_id>/start')
api.add_resource(PipelineStop, '/pipelines/<pipeline_id>/stop')
api.add_resource(PipelineExport, '/pipelines/<pipeline_id>/export')
api.add_resource(PipelineImport, '/pipelines/import')
api.add_resource(
    PipelineRunOnSchedule,
    '/pipelines/<pipeline_id>/run_on_schedule'
)
api.add_resource(PipelineLogs, '/pipelines/<pipeline_id>/logs')
