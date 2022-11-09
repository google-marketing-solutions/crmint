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

"""Job section."""

from flask import Blueprint
from flask_restful import abort
from flask_restful import Api
from flask_restful import fields
from flask_restful import marshal_with
from flask_restful import reqparse
from flask_restful import Resource

from common import insight
from controller import models

blueprint = Blueprint('job', __name__)
api = Api(blueprint)

parser = reqparse.RequestParser()
parser.add_argument('name')
parser.add_argument('worker_class')
parser.add_argument('pipeline_id')
parser.add_argument('start_conditions', type=list, location='json')
parser.add_argument('params', type=list, location='json')
param_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'type': fields.String,
    'value': fields.Raw(attribute='api_value'),
    'label': fields.String
}
start_condition_fields = {
    'id': fields.Integer,
    'job_id': fields.Integer,
    'preceding_job_id': fields.Integer,
    'preceding_job_name': fields.String,
    'condition': fields.String,
}
job_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'status': fields.String,
    'updated_at': fields.String,
    'worker_class': fields.String,
    'start_conditions': fields.List(fields.Nested(start_condition_fields)),
    'pipeline_id': fields.Integer,
    'params': fields.List(fields.Nested(param_fields)),
    'message': fields.String
}


def abort_if_job_doesnt_exist(job, job_id):
  if job is None:
    abort(404, message="Job {} doesn't exist".format(job_id))


class JobSingle(Resource):
  """Shows a single job item and lets you delete a job item."""

  @marshal_with(job_fields)
  def get(self, job_id):
    job = models.Job.find(job_id)
    abort_if_job_doesnt_exist(job, job_id)
    return job

  @marshal_with(job_fields)
  def delete(self, job_id):
    job = models.Job.find(job_id)
    abort_if_job_doesnt_exist(job, job_id)

    if job.pipeline.is_blocked():
      return {
          'message': 'Removing of job for active pipeline is unavailable'
      }, 422

    job.destroy()
    tracker = insight.GAProvider()
    tracker.track_event(category='jobs', action='delete')
    return {}, 204

  @marshal_with(job_fields)
  def put(self, job_id):
    job = models.Job.find(job_id)
    abort_if_job_doesnt_exist(job, job_id)

    if job.pipeline.is_blocked():
      return {
          'message': 'Editing of job for active pipeline is unavailable'
      }, 422

    args = parser.parse_args()

    job.assign_attributes(args)
    job.save()
    job.save_relations(args)
    return job, 200


class JobList(Resource):
  """Shows a list of all jobs, and lets you POST to add new jobs."""

  @marshal_with(job_fields)
  def get(self):
    args = parser.parse_args()
    pipeline = models.Pipeline.find(args['pipeline_id'])
    jobs = pipeline.jobs
    return jobs

  @marshal_with(job_fields)
  def post(self):
    args = parser.parse_args()
    pipeline = models.Pipeline.find(args['pipeline_id'])

    if pipeline.is_blocked():
      return {
          'message': 'Creating new jobs for active pipeline is unavailable'
      }, 422

    job = models.Job(args['name'], args['worker_class'], args['pipeline_id'])
    job.assign_attributes(args)
    job.save()
    job.save_relations(args)
    tracker = insight.GAProvider()
    tracker.track_event(
        category='jobs',
        action='create',
        label=args['worker_class'])
    return job, 201


class JobStart(Resource):
  """Class for running of job."""

  @marshal_with(job_fields)
  def post(self, job_id):
    job = models.Job.find(job_id)
    job.pipeline.start_single_job(job)
    tracker = insight.GAProvider()
    tracker.track_event(
        category='jobs',
        action='manual_run',
        label=job.worker_class)
    return job


api.add_resource(JobList, '/jobs')
api.add_resource(JobSingle, '/jobs/<job_id>')
api.add_resource(JobStart, '/jobs/<job_id>/start')
