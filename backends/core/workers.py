# Copyright 2019 Google Inc. All rights reserved.
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

"""Module with CRMintApp worker classes."""

from datetime import datetime
from datetime import timedelta
from fnmatch import fnmatch
from functools import wraps
from pprint import pprint
import json
import os
from random import random
import time
import urllib
from urllib2 import HTTPError
import uuid
import yaml

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaIoBaseUpload
import cloudstorage as gcs
from google.cloud import bigquery
from google.cloud.exceptions import ClientError
from googleads import adwords
from oauth2client.service_account import ServiceAccountCredentials
import requests
import zeep.cache


_KEY_FILE = os.path.join(os.path.dirname(__file__), '..', 'data',
                         'service-account.json')
AVAILABLE = (
    'AutoMLImporter',
    'AutoMLPredictor',
    'AutoMLTrainer',
    'BQMLTrainer',
    'BQQueryLauncher',
    'BQToAppConversionAPI',
    'BQToCM',
    'BQToMeasurementProtocol',
    'BQToMeasurementProtocolGA4',
    'BQToStorageExporter',
    'Commenter',
    'GAAudiencesUpdater',
    'GADataImporter',
    'GAGoalsUpdater',
    'GAToBQImporter',
    'MLPredictor',
    'MLTrainer',
    'MLVersionDeployer',
    'StorageChecker',
    'StorageCleaner',
    'StorageToBQImporter',
)

# Defines how many times to retry a function wrapped in Worker.retry()
# on failure, 3 times by default.
DEFAULT_MAX_RETRIES = os.environ.get('MAX_RETRIES', 3)

# pylint: disable=too-few-public-methods

class WorkerException(Exception):
  """Worker execution exceptions expected in task handler."""


class Worker(object):
  """Abstract worker class."""

  # A list describing worker parameters. Each element in the list is a tuple
  # of five elements: 0) parameter's name, 1) parameter's type, 2) True if
  # parameter is required, False otherwise, 3) default value to use when
  # parameter value is missing, and 4) label to show near parameter's field in
  # a web UI. See examples below in worker classes.
  PARAMS = []

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

  def _log(self, level, message, *substs):
    from core import cloud_logging
    self.retry(cloud_logging.logger.log_struct)({
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
    try:
      self._execute()
    except ClientError as e:
      raise WorkerException(e)
    self.log_info('Finished successfully')
    return self._workers_to_enqueue

  def _execute(self):
    """Abstract method that does actual worker's job."""
    pass

  def _enqueue(self, worker_class, worker_params, delay=0):
    self._workers_to_enqueue.append((worker_class, worker_params, delay))

  def retry(self, func, max_retries=DEFAULT_MAX_RETRIES):
    """Decorator implementing retries with exponentially increasing delays."""
    @wraps(func)
    def func_with_retries(*args, **kwargs):
      """Retriable version of function being decorated."""
      tries = 0
      while tries < max_retries:
        try:
          return func(*args, **kwargs)
        except HttpError as e:
          # If it is a client side error, then there's no reason to retry.
          if e.resp.status > 399 and e.resp.status < 500:
            raise e
        except HTTPError as e:
          # If it is a client side error, then there's no reason to retry.
          if e.code > 399 and e.code < 500:
            raise e
        except Exception as e:  # pylint: disable=broad-except
          pass
        tries += 1
        delay = 5 * 2 ** (tries + random())
        time.sleep(delay)
      return func(*args, **kwargs)
    return func_with_retries


class Commenter(Worker):
  """Dummy worker that fails when checkbox is unchecked."""

  PARAMS = [
      ('comment', 'text', False, '', 'Comment'),
      ('success', 'boolean', True, False, 'Finish successfully'),
  ]

  def _execute(self):
    if not self._params['success']:
      msg = '"{}" is unchecked: {}'.format(
          self.PARAMS[1][4],
          self._params['comment'])
      raise WorkerException(msg)


class BQWorker(Worker):
  """Abstract BigQuery worker."""

  def _get_client(self):
    bigquery.Client.SCOPE = (
        'https://www.googleapis.com/auth/bigquery',
        'https://www.googleapis.com/auth/cloud-platform',
        'https://www.googleapis.com/auth/drive')
    client = bigquery.Client.from_service_account_json(_KEY_FILE)
    if self._params['bq_project_id'].strip():
      client.project = self._params['bq_project_id']
    return client

  def _bq_setup(self):
    self._client = self._get_client()
    self._dataset = self._client.dataset(self._params['bq_dataset_id'])
    self._table = self._dataset.table(self._params['bq_table_id'])
    self._job_name = '%i_%i_%s_%s' % (self._pipeline_id, self._job_id,
                                      self.__class__.__name__, uuid.uuid4())

  def _begin_and_wait(self, *jobs):
    for job in jobs:
      job.begin()
    delay = 5
    wait_time = 0
    all_jobs_done = False
    while not all_jobs_done:
      wait_time += delay
      if wait_time > 300:  # If 5 minutes passed, then spawn BQWaiter.
        worker_params = {
            'job_names': [job.name for job in jobs],
            'bq_project_id': self._params['bq_project_id']
        }
        self._enqueue('BQWaiter', worker_params, 60)
        return
      time.sleep(delay)
      if delay < 30:
        delay = [5, 10, 15, 20, 30][wait_time / 60]
      all_jobs_done = True
      for job in jobs:
        job.reload()
        if job.error_result is not None:
          raise WorkerException(job.error_result['message'])
        if job.state != 'DONE':
          all_jobs_done = False
          break


class BQWaiter(BQWorker):
  """Worker that checks BQ job status and respawns itself if job is running."""

  def _execute(self):
    client = self._get_client()
    for job_name in self._params['job_names']:
      # pylint: disable=protected-access
      job = bigquery.job._AsyncJob(job_name, client)
      # pylint: enable=protected-access
      job.reload()
      if job.error_result is not None:
        raise WorkerException(job.error_result['message'])
      if job.state != 'DONE':
        worker_params = {
            'job_names': self._params['job_names'],
            'bq_project_id': self._params['bq_project_id']
        }
        self._enqueue('BQWaiter', worker_params, 60)
        return


class BQQueryLauncher(BQWorker):
  """Worker to run SQL queries in BigQuery."""

  PARAMS = [
      ('query', 'sql', True, '', 'Query'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('overwrite', 'boolean', True, False, 'Overwrite table'),
  ]

  def _execute(self):
    self._bq_setup()
    job = self._client.run_async_query(self._job_name, self._params['query'])
    job.destination = self._table
    job.use_legacy_sql = False
    if self._params['overwrite']:
      job.write_disposition = 'WRITE_TRUNCATE'
    else:
      job.write_disposition = 'WRITE_APPEND'
    self._begin_and_wait(job)


class StorageWorker(Worker):
  """Abstract worker class for Cloud Storage workers."""

  def _get_matching_stats(self, patterned_uris):
    stats = []
    patterns = {}
    for patterned_uri in patterned_uris:
      patterned_uri_split = patterned_uri.split('/')
      bucket = '/'.join(patterned_uri_split[1:3])
      pattern = '/'.join(patterned_uri_split[1:])
      try:
        if pattern not in patterns[bucket]:
          patterns[bucket].append(pattern)
      except KeyError:
        patterns[bucket] = [pattern]
    for bucket in patterns:
      for stat in gcs.listbucket(bucket):
        if not stat.is_dir:
          for pattern in patterns[bucket]:
            if fnmatch(stat.filename, pattern):
              stats.append(stat)
              break
    return stats


class StorageCleaner(StorageWorker):
  """Worker to delete stale files in Cloud Storage."""

  PARAMS = [
      ('file_uris', 'string_list', True, '',
       ('List of file URIs and URI patterns (e.g. gs://bucket/data.csv or '
        'gs://bucket/data_*.csv)')),
      ('expiration_days', 'number', True, 30,
       'Days to keep files since last modification'),
  ]

  def _execute(self):
    delta = timedelta(self._params['expiration_days'])
    expiration_datetime = datetime.now() - delta
    expiration_timestamp = time.mktime(expiration_datetime.timetuple())
    stats = self._get_matching_stats(self._params['file_uris'])
    for stat in stats:
      if stat.st_ctime < expiration_timestamp:
        gcs.delete(stat.filename)
        self.log_info('gs:/%s file deleted.', stat.filename)


class StorageChecker(StorageWorker):
  """Worker to check if files matching the patterns exist in Cloud Storage."""

  PARAMS = [
      ('file_uris', 'string_list', True, '',
       ('List of file URIs and URI patterns (e.g. gs://bucket/data.csv or '
        'gs://bucket/data_*.csv)')),
      ('min_size', 'number', False, '',
       'Least total size of matching files in bytes required for success'),
  ]

  def _execute(self):
    try:
      min_size = int(self._params['min_size'])
    except TypeError:
      min_size = 0
    stats = self._get_matching_stats(self._params['file_uris'])
    if not stats:
      raise WorkerException('Files matching the patterns were not found')
    size = reduce(lambda total, stat: total + stat.st_size, stats, 0)
    if size < min_size:
      raise WorkerException('Files matching the patterns are too small')



class StorageToBQImporter(StorageWorker, BQWorker):
  """Worker to import a CSV file into a BigQuery table."""

  PARAMS = [
      ('source_uris', 'string_list', '', True,
       'Source CSV or JSON files URIs (e.g. gs://bucket/data.csv)'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('overwrite', 'boolean', True, False, 'Overwrite table'),
      ('dont_create', 'boolean', True, False,
       'Don\'t create table if doesn\'t exist'),
      ('autodetect', 'boolean', True, False,
       'Autodetect schema and other parameters'),
      ('rows_to_skip', 'number', False, 0, 'Header rows to skip'),
      ('errors_to_allow', 'number', False, 0, 'Number of errors allowed'),
      ('import_json', 'boolean', False, False, 'Source is in JSON format'),
      ('csv_null_marker', 'string', False, '', 'CSV Null marker'),
      ('schema', 'text', False, '', 'Table Schema in JSON'),
  ]

  def _get_source_uris(self):
    stats = self._get_matching_stats(self._params['source_uris'])
    return ['gs:/%s' % s.filename for s in stats]


  def _get_field_schema(self, field):
    name = field['name']
    field_type = field.get('type', 'STRING')
    mode = field.get('mode', 'NULLABLE')
    fields = field.get('fields', [])

    if fields:
      subschema = []
      for f in fields:
        fields_res = self._get_field_schema(f)
        subschema.append(fields_res)
    else:
      subschema = []

    field_schema = bigquery.schema.SchemaField(
      name=name,
      field_type=field_type,
      mode=mode,
      fields=tuple(subschema)
    )

    return field_schema

  def _parse_bq_json_schema(self, schema_json_string):
    table_schema = []
    jsonschema = json.loads(schema_json_string)

    for field in jsonschema:
      table_schema.append(self._get_field_schema(field))

    return table_schema

  def _execute(self):
    self._bq_setup()
    source_uris = self._get_source_uris()
    job = self._client.load_table_from_storage(
        self._job_name, self._table, *source_uris)
    if self._params['import_json']:
      job.source_format = 'NEWLINE_DELIMITED_JSON'
    else:
      try:
        job.skip_leading_rows = self._params['rows_to_skip']
      except KeyError:
        job.skip_leading_rows = 0
    job.autodetect = self._params['autodetect']

    if self._params['csv_null_marker']:
      job.null_marker = self._params['csv_null_marker']

    if job.autodetect:
      # Ugly patch to make autodetection work. See https://goo.gl/shWLKf
      # pylint: disable=protected-access
      def _build_resource_with_autodetect():
        resource = bigquery.job.LoadTableFromStorageJob._build_resource(job)
        resource['configuration']['load']['autodetect'] = True
        return resource
      job._build_resource = _build_resource_with_autodetect
      # pylint: enable=protected-access
    else:
      job.allow_jagged_rows = True
      job.allow_quoted_newlines = True
      job.ignore_unknown_values = True

      if self._params['schema']:
        job.schema = self._parse_bq_json_schema(self._params['schema'])

    try:
      job.max_bad_records = self._params['errors_to_allow']
    except KeyError:
      job.max_bad_records = 0
    if self._params['overwrite']:
      job.write_disposition = 'WRITE_TRUNCATE'
    else:
      job.write_disposition = 'WRITE_APPEND'
    if self._params['dont_create']:
      job.create_disposition = 'CREATE_NEVER'
    else:
      job.create_disposition = 'CREATE_IF_NEEDED'
    self._begin_and_wait(job)


class BQToStorageExporter(BQWorker):
  """Worker to export a BigQuery table to a CSV file."""

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('destination_uri', 'string', True, '',
       'Destination CSV or JSON file URI (e.g. gs://bucket/data.csv)'),
      ('print_header', 'boolean', True, False, 'Include a header row'),
      ('export_json', 'boolean', False, False, 'Export in JSON format'),
  ]

  def _execute(self):
    self._bq_setup()
    job = self._client.extract_table_to_storage(
        self._job_name, self._table, self._params['destination_uri'])
    job.print_header = self._params['print_header']
    if self._params['export_json']:
      job.destination_format = 'NEWLINE_DELIMITED_JSON'
    self._begin_and_wait(job)


class GAWorker(Worker):
  """Abstract class with GA-specific methods."""

  def _ga_setup(self, v='v4'):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(_KEY_FILE)
    service = 'analyticsreporting' if v == 'v4' else 'analytics'
    self._ga_client = build(service, v, credentials=credentials)

  def _parse_accountid_from_propertyid(self):
    return self._params['property_id'].split('-')[1]


class GAToBQImporter(BQWorker, GAWorker):
  """Worker to load data into BQ from GA using Core Reporting API."""

  PARAMS = [
      ('view_ids', 'string_list', True, '', 'View IDs (e.g. 12345)'),
      ('start_date', 'string', True, '', 'Start date (e.g. 2015-12-31)'),
      ('end_date', 'string', True, '', 'End date (e.g. 2016-12-31)'),
      ('day_by_day', 'boolean', True, False, 'Fetch data day by day'),
      ('metrics', 'string_list', True, '', 'Metrics (e.g. ga:users)'),
      ('dimensions', 'string_list', False, '', 'Dimensions (e.g. ga:source)'),
      ('filters', 'string', False, '',
       'Filters (e.g. ga:deviceCategory==mobile)'),
      ('include_empty_rows', 'boolean', True, False, 'Include empty rows'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
  ]

  def _compose_report(self):
    dimensions = [{'name': d} for d in self._params['dimensions']]
    metrics = [{'expression': m} for m in self._params['metrics']]
    self._request = {
        'viewId': None,
        'dateRanges': None,
        'dimensions': dimensions,
        'metrics': metrics,
        'filtersExpression': self._params['filters'],
        'hideTotals': True,
        'hideValueRanges': True,
        'includeEmptyRows': self._params['include_empty_rows'],
        'samplingLevel': 'LARGE',
        'pageSize': 10000,
    }

  def _get_report(self, view_id, start_date, end_date):
    # TODO(dulacp): refactor this method, too complex branching logic

    log_str = 'View ID %s from %s till %s' % (view_id, start_date, end_date)
    self.log_info('Fetch for %s started', log_str)
    rows_fetched = 0
    self._request['view_id'] = view_id
    self._request['dateRanges'] = [{
        'startDate': start_date,
        'endDate': end_date,
    }]
    body = {'reportRequests': [self._request]}
    while True:
      request = self._ga_client.reports().batchGet(body=body)
      response = self.retry(request.execute)()
      report = response['reports'][0]
      dimensions = [d.replace(':', '_') for d in
                    report['columnHeader']['dimensions']]
      metrics = [m['name'].replace(':', '_') for m in
                 report['columnHeader']['metricHeader']['metricHeaderEntries']]
      ga_row = {
          'view_id': view_id,
          'start_date': start_date,
          'end_date': end_date,
      }
      try:
        for row in report['data']['rows']:
          for dimension, value in zip(dimensions, row['dimensions']):
            ga_row[dimension] = value
          for metric, value in zip(metrics, row['metrics'][0]['values']):
            ga_row[metric] = value
          bq_row = []
          for field in self._table.schema:
            try:
              bq_row.append(ga_row[field.name])
            except KeyError:
              bq_row.append(None)
          self._bq_rows.append(tuple(bq_row))
        self._flush()
        rows_fetched += len(report['data']['rows'])
        try:
          self._request['pageToken'] = report['nextPageToken']
        except KeyError:
          try:
            del self._request['pageToken']
          except KeyError:
            pass
          break
      except KeyError:
        break
    if rows_fetched:
      self.log_info('%i rows of data fetched for %s', rows_fetched, log_str)
    else:
      self.log_warn('No rows of data fetched for %s', log_str)

  def _flush(self, forced=False):
    if self._bq_rows:
      if forced or len(self._bq_rows) > 9999:
        for i in xrange(0, len(self._bq_rows), 10000):
          self._table.insert_data(self._bq_rows[i:i + 10000])
        self._bq_rows = []

  def _execute(self):
    self._bq_setup()
    self._table.reload()
    self._ga_setup()
    self._compose_report()
    self._bq_rows = []
    if self._params['day_by_day']:
      start_date = datetime.strptime(
          self._params['start_date'], '%Y-%m-%d').date()
      end_date = datetime.strptime(
          self._params['end_date'], '%Y-%m-%d').date()
      date_str = start_date.strftime('%Y-%m-%d')
      for view_id in self._params['view_ids']:
        self._get_report(view_id, date_str, date_str)
      self._flush(forced=True)
      if start_date != end_date:
        start_date += timedelta(1)
        params = self._params.copy()
        params['start_date'] = start_date.strftime('%Y-%m-%d')
        self._enqueue(self.__class__.__name__, params)
    else:
      for view_id in self._params['view_ids']:
        self._get_report(
            view_id, self._params['start_date'], self._params['end_date'])
      self._flush(forced=True)


class GADataImporter(GAWorker):
  """Imports CSV data from Cloud Storage to GA using Data Import."""

  PARAMS = [
      ('csv_uri', 'string', True, '',
       'CSV data file URI (e.g. gs://bucket/data.csv)'),
      ('property_id', 'string', True, '',
       'GA Property Tracking ID (e.g. UA-12345-3)'),
      ('dataset_id', 'string', True, '',
       'GA Dataset ID (e.g. sLj2CuBTDFy6CedBJw)'),
      ('max_uploads', 'number', False, '',
       'Maximum uploads to keep in GA Dataset (leave empty to keep all)'),
      ('delete_before', 'boolean', True, False,
       'Delete older uploads before upload'),
      ('account_id', 'string', False, '', 'GA Account ID'),
  ]

  _BUFFER_SIZE = 256 * 1024

  def _upload(self):
    with gcs.open(self._file_name, read_buffer_size=self._BUFFER_SIZE) as f:
      media = MediaIoBaseUpload(f, mimetype='application/octet-stream',
                                chunksize=self._BUFFER_SIZE, resumable=True)
      request = self._ga_client.management().uploads().uploadData(
          accountId=self._account_id,
          webPropertyId=self._params['property_id'],
          customDataSourceId=self._params['dataset_id'],
          media_body=media)
      response = None
      tries = 0
      milestone = 0
      while response is None and tries < 5:
        try:
          status, response = request.next_chunk()
        except HttpError, e:
          if e.resp.status in [404, 500, 502, 503, 504]:
            tries += 1
            delay = 5 * 2 ** (tries + random())
            self.log_warn('%s, Retrying in %.1f seconds...', e, delay)
            time.sleep(delay)
          else:
            raise WorkerException(e)
        else:
          tries = 0
        if status:
          progress = int(status.progress() * 100)
          if progress >= milestone:
            self.log_info('Uploaded %d%%.', int(status.progress() * 100))
            milestone += 20
      self.log_info('Upload Complete.')

  def _delete_older(self, uploads_to_keep):
    request = self._ga_client.management().uploads().list(
        accountId=self._account_id, webPropertyId=self._params['property_id'],
        customDataSourceId=self._params['dataset_id'])
    response = self.retry(request.execute)()
    uploads = sorted(response.get('items', []), key=lambda u: u['uploadTime'])
    if uploads_to_keep:
      ids_to_delete = [u['id'] for u in uploads[:-uploads_to_keep]]
    else:
      ids_to_delete = [u['id'] for u in uploads]
    if ids_to_delete:
      request = self._ga_client.management().uploads().deleteUploadData(
          accountId=self._account_id,
          webPropertyId=self._params['property_id'],
          customDataSourceId=self._params['dataset_id'],
          body={
              'customDataImportUids': ids_to_delete})
      self.retry(request.execute)()
      self.log_info('%i older upload(s) deleted.', len(ids_to_delete))

  def _execute(self):
    self._ga_setup('v3')
    if self._params['account_id']:
      self._account_id = self._params['account_id']
    else:
      self._account_id = self._parse_accountid_from_propertyid()
    self._file_name = self._params['csv_uri'].replace('gs:/', '')
    if self._params['max_uploads'] > 0 and self._params['delete_before']:
      self._delete_older(self._params['max_uploads'] - 1)
    self._upload()
    if self._params['max_uploads'] > 0 and not self._params['delete_before']:
      self._delete_older(self._params['max_uploads'])


class GAAudiencesUpdater(BQWorker, GAWorker):
  """Worker to update GA audiences using values from a BQ table.

  See: https://developers.google.com/analytics/devguides/config/mgmt/v3/mgmtReference/management/remarketingAudience#resource
  for more details on the required GA Audience JSON template format.
  """

  PARAMS = [
      ('property_id', 'string', True, '',
       'GA Property Tracking ID (e.g. UA-12345-3)'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('template', 'text', True, '', 'GA audience JSON template'),
      ('account_id', 'string', False, '', 'GA Account ID'),
  ]

  def _infer_audiences(self):
    self._inferred_audiences = {}
    fields = [f.name for f in self._table.schema]
    for row in self._table.fetch_data():
      try:
        template_rendered = self._params['template'] % dict(zip(fields, row))
        audience = json.loads(template_rendered)
      except ValueError as e:
        raise WorkerException(e)
      self._inferred_audiences[audience['name']] = audience

  def _get_audiences(self):
    audiences = []
    start_index = 1
    max_results = 100
    total_results = 100
    while start_index <= total_results:
      request = self._ga_client.management().remarketingAudience().list(
          accountId=self._account_id,
          webPropertyId=self._params['property_id'],
          start_index=start_index,
          max_results=max_results)
      response = self.retry(request.execute)()
      total_results = response['totalResults']
      start_index += max_results
      audiences += response['items']
    self._current_audiences = {}
    names = self._inferred_audiences.keys()
    for audience in audiences:
      if audience['name'] in names:
        self._current_audiences[audience['name']] = audience

  def _equal(self, patch, audience):
    """Checks whether applying a patch would not change an audience.

    Args:
        patch: An object that is going to be used as a patch to update the
            audience.
        audience: An object representing audience to be patched.

    Returns:
       True if applying the patch won't change the audience, False otherwise.
    """
    dicts = [(patch, audience)]
    for d1, d2 in dicts:
      keys = d1 if isinstance(d1, dict) else xrange(len(d1))
      for k in keys:
        try:
          d2[k]
        except (IndexError, KeyError):
          return False
        if isinstance(d1[k], dict):
          if isinstance(d2[k], dict):
            dicts.append((d1[k], d2[k]))
          else:
            return False
        elif isinstance(d1[k], list):
          if isinstance(d2[k], list) and len(d1[k]) == len(d2[k]):
            dicts.append((d1[k], d2[k]))
          else:
            return False
        elif d1[k] != d2[k]:
          return False
    return True

  def _get_diff(self):
    """Composes lists of audiences to be created and updated in GA."""
    self._audiences_to_insert = []
    self._audiences_to_patch = {}
    for name in self._inferred_audiences:
      inferred_audience = self._inferred_audiences[name]
      if name in self._current_audiences:
        current_audience = self._current_audiences[name]
        if not self._equal(inferred_audience, current_audience):
          self._audiences_to_patch[current_audience['id']] = inferred_audience
      else:
        self._audiences_to_insert.append(inferred_audience)

  def _update_ga_audiences(self):
    """Updates and/or creates audiences in GA."""
    for audience in self._audiences_to_insert:
      request = self._ga_client.management().remarketingAudience().insert(
          accountId=self._account_id,
          webPropertyId=self._params['property_id'],
          body=audience)
      self.retry(request.execute)()
    for audience_id in self._audiences_to_patch:
      audience = self._audiences_to_patch[audience_id]
      request = self._ga_client.management().remarketingAudience().patch(
          accountId=self._account_id,
          webPropertyId=self._params['property_id'],
          remarketingAudienceId=audience_id,
          body=audience)
      self.retry(request.execute)()

  def _execute(self):
    if self._params['account_id']:
      self._account_id = self._params['account_id']
    else:
      self._account_id = self._parse_accountid_from_propertyid()
    self._bq_setup()
    self._table.reload()
    self._ga_setup('v3')
    self._infer_audiences()
    self._get_audiences()
    self._get_diff()
    self._update_ga_audiences()

    
class GAGoalsUpdater(BQWorker, GAWorker):
  """Worker to update GA goals using values from a BQ table.
  See: https://developers.google.com/analytics/devguides/config/mgmt/v3/mgmtReference/management/goals#resource-representations
  for more details on the required GA Goal JSON template format.
  """

  PARAMS = [
      ('property_id', 'string', True, '',
       'GA Property Tracking ID (e.g. UA-12345-3)'),
      ('view_id', 'string', True, '', 'GA View ID (e.g. 345678)'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('template', 'text', True, '', 'GA goal JSON template'),
      ('account_id', 'string', False, '', 'GA Account ID'),
  ]

  def _infer_goals(self):
    self._inferred_goals = {}
    fields = [f.name for f in self._table.schema]
    for row in self._table.fetch_data():
      try:
        template_rendered = self._params['template'] % (
          dict(zip(fields, row)))
        goal = json.loads(template_rendered)
      except ValueError as e:
        raise WorkerException(e)
      self._inferred_goals[goal['name']] = goal

  def _get_goals(self):
    goals = []
    start_index = 1
    max_results = 100
    total_results = 100
    while start_index <= total_results:
      request = self._ga_client.management().goals().list(
          accountId=self._account_id,
          webPropertyId=self._params['property_id'],
          profileId=self._params['view_id'],
          start_index=start_index,
          max_results=max_results)
      response = self.retry(request.execute)()
      total_results = response['totalResults']
      start_index += max_results
      goals += response['items']
    self._current_goals = {}
    names = self._inferred_goals.keys()
    for goal in goals:
      if goal['name'] in names:
        self._current_goals[goal['name']] = goal

  def _equal(self, patch, goal):
    """Checks whether applying a patch would not change a goal.
    Args:
        patch: An object that is going to be used as a patch
            to update the goal.
        goal: An object representing goal to be patched.
    Returns:
       True if applying the patch won't change the goal, False otherwise.
    """
    dicts = [(patch, goal)]
    for d1, d2 in dicts:
      keys = d1 if isinstance(d1, dict) else xrange(len(d1))
      for k in keys:
        try:
          d2[k]
        except (IndexError, KeyError):
          return False
        if isinstance(d1[k], dict):
          if isinstance(d2[k], dict):
            dicts.append((d1[k], d2[k]))
          else:
            return False
        elif isinstance(d1[k], list):
          if isinstance(d2[k], list) and len(d1[k]) == len(d2[k]):
            dicts.append((d1[k], d2[k]))
          else:
            return False
        elif d1[k] != d2[k]:
          return False
    return True

  def _get_diff(self):
    """Composes lists of goals to be created and updated in GA."""
    self._goals_to_insert = []
    self._goals_to_patch = {}
    for name in self._inferred_goals:
      inferred_goal = self._inferred_goals[name]
      if name in self._current_goals:
        current_goal = self._current_goals[name]
        if not self._equal(inferred_goal, current_goal):
          self._goals_to_patch[current_goal['id']] = inferred_goal
      else:
        self._goals_to_insert.append(inferred_goal)

  def _update_ga_goals(self):
    """Updates and/or creates goals in GA."""
    for goal in self._goals_to_insert:
      request = self._ga_client.management().goals().insert(
          accountId=self._account_id,
          webPropertyId=self._params['property_id'],
          profileId=self._params['view_id'],
          body=goal)
      self.retry(request.execute)()
    for goal_id in self._goals_to_patch:
      goal = self._goals_to_patch[goal_id]
      request = self._ga_client.management().goals().patch(
          accountId=self._account_id,
          webPropertyId=self._params['property_id'],
          profileId=self._params['view_id'],
          goalId=goal_id,
          body=goal)
      self.retry(request.execute)()

  def _execute(self):
    if self._params['account_id']:
      self._account_id = self._params['account_id']
    else:
      self._account_id = self._parse_accountid_from_propertyid()
    self._bq_setup()
    self._table.reload()
    self._ga_setup('v3')
    self._infer_goals()
    self._get_goals()
    self._get_diff()
    self._update_ga_goals()    


class MLWorker(Worker):
  """Abstract ML Engine worker."""

  def _get_ml_client(self):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(_KEY_FILE)
    self._ml_client = build('ml', 'v1', credentials=credentials)

  def _get_ml_job_id(self):
    self._ml_job_id = '%s_%i_%i_%s' % (self.__class__.__name__,
                                       self._pipeline_id, self._job_id,
                                       str(uuid.uuid4()).replace('-', '_'))


class MLWaiter(MLWorker):
  """Worker that checks ML job status and respawns itself if job is running."""

  FINAL_STATUSES = ('STATE_UNSPECIFIED', 'SUCCEEDED', 'FAILED', 'CANCELLED')

  def _execute(self):
    self._get_ml_client()
    request = self._ml_client.projects().jobs().get(
        name=self._params['job_name'])
    job = self.retry(request.execute)()
    if job.get('state') not in self.FINAL_STATUSES:
      self._enqueue('MLWaiter', {'job_name': self._params['job_name']}, 60)

class MLOperationWaiter(MLWorker):
  """ Worker that checks an ML operation's status and respawns'
  'itslef until the operation is done."""

  def _execute(self):
    self._get_ml_client()
    request = self._ml_client.projects().operations().get(
        name=self._params['operation_name'])
    operation = self.retry(request.execute)()
    if operation['done'] != True:
      self._enqueue('MLOperationWaiter',
                    {'operation_name': self._params['operation_name']}, 60)

class MLPredictor(MLWorker):
  """Worker to create ML batch prediction jobs."""

  PARAMS = [
      ('project', 'string', True, '', 'ML project ID'),
      ('model', 'string', True, '', 'ML model name'),
      ('version', 'string', True, '', 'ML model version'),
      ('input_uris', 'string_list', True, '',
       'URIs of input JSON files (e.g. gs://bucket/data.json)'),
      ('output_uri', 'string', True, '',
       'URI of folder to put predictions into (e.g. gs://bucket/folder)'),
  ]

  def _execute(self):
    project_id = 'projects/%s' % self._params['project']
    version_name = '%s/models/%s/versions/%s' % (
        project_id, self._params['model'], self._params['version'])
    self._get_ml_job_id()
    body = {
        'jobId': self._ml_job_id,
        'predictionInput': {
            'dataFormat': 'JSON',
            'inputPaths': self._params['input_uris'],
            'outputPath': self._params['output_uri'],
            'region': 'europe-west1',
            'versionName': version_name,
        }
    }
    self._get_ml_client()
    request = self._ml_client.projects().jobs().create(parent=project_id,
                                                       body=body)
    self.retry(request.execute)()
    job_name = '%s/jobs/%s' % (project_id, self._ml_job_id)
    self._enqueue('MLWaiter', {'job_name': job_name}, 60)

class MLTrainer(MLWorker):
  """Worker to train a ML model"""

  PARAMS = [
      ('project', 'string', True, '', 'ML project ID'),
      ('jobDir', 'string', True, '',
       'URI of folder to put output generated by AI platform '
       '(e.g. gs://bucket/folder)'),
      ('packageUris', 'string', True, '',
       'URI of python package e.g. gs://bucket/folder/filename.tar.gz'),
      ('scaleTier', 'string', True, '',
       'Scale Tier e.g. BASIC, STANDARD_1'),
      ('runtimeVersion', 'string', True, '',
       'Runtime version e.g. 1.10'),
      ('pythonModule', 'string', True, '',
       'Name of python module e.g. trainer.task'),
      ('args', 'string_list', True, '',
       'Enter the arguments to be passed to the python package. '
       'Key in one line, value in the next.')
  ]
  def _execute(self):

    self._get_ml_job_id()
    body = {
        'jobId': self._ml_job_id,
        'trainingInput': {
            'args': [a.strip() for a in self._params['args']],
            'packageUris': self._params['packageUris'],
            'region': 'europe-west1',
            'jobDir': self._params['jobDir'],
            'runtimeVersion': self._params['runtimeVersion'],
            'pythonModule': '%s' % (self._params['pythonModule'])
        }
    }

    project_id = 'projects/%s' % self._params['project']
    self._get_ml_client()
    request = self._ml_client.projects().jobs().create(
        parent=project_id, body=body)
    self.retry(request.execute)()
    job_name = '%s/jobs/%s' % (project_id, self._ml_job_id)
    self._enqueue('MLWaiter', {'job_name': job_name}, 60)

class MLVersionDeployer(MLWorker, StorageWorker):
  """Worker to deploy ML Model Version"""

  PARAMS = [
      ('project', 'string', True, '', 'ML project ID'),
      ('jobDir', 'string', True, '',
       'URI of GCS folder with a trained model'
       '(e.g. gs://bucket/folder)'),
      ('modelName', 'string', True, '',
       'Name of the ML model in Google Cloud AI Platform'),
      ('versionName', 'string', True, '',
       'Name of the version (letters, numbers, underscores only; '
       'must start with a letter)'),
      ('runtimeVersion', 'string', True, '',
       'Runtime version e.g. 1.10'),
      ('pythonVersion', 'string', True, '', 'Version of python, e.g. 3.5'),
      ('framework', 'string', True, '', 'Framework, eg. TENSORFLOW')
  ]

  def _execute(self):
    self._get_ml_job_id()

    # Find directory where newest saved model is located
    bucket = self._params['jobDir']
    stats = gcs.listbucket(bucket[4:])
    newest_file = None

    for stat in stats:
      if stat.filename.find('saved_model.pb') != -1:
        if newest_file is None:
          newest_file = stat
          if newest_file:
            if stat.st_ctime > newest_file.st_ctime:
              newest_file = stat

    body = {
       	"name": self._params['versionName'],
       	"description": "Test from python",
       	"deploymentUri": ("gs:/" + newest_file.
                          filename[0:newest_file.filename.rfind('/')]),
       	"pythonVersion": self._params['pythonVersion'],
       	"runtimeVersion": self._params['runtimeVersion'],
       	"framework": self._params['framework']
    }

    project_id = 'projects/%s' % self._params['project']
    self._get_ml_client()
    request = self._ml_client.projects().models().versions().create(
        parent=project_id + "/models/" + self._params['modelName'], body=body)
    response = self.retry(request.execute)()
    self._enqueue('MLOperationWaiter', {'operation_name': response['name']}, 60)


class MeasurementProtocolException(WorkerException):
  """Measurement Protocol execution exception."""
  pass


class BQToMeasurementProtocolGA4(BQWorker):
  """Worker to push data through Measurement Protocol."""

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('measurement_id', 'string', True, '', 'Measurement ID'),
      ('api_secret', 'string', True, '', 'API Secret'),
      ('template', 'text', True, '', ('GA4 Measurement Protocol '
                                      'JSON template')),
      ('mp_batch_size', 'number', True, 20, ('Measurement Protocol '
                                             'batch size')),
      ('debug', 'boolean', True, False, 'Debug mode'),
  ]

  # BigQuery batch size for querying results. Default to 1000.
  BQ_BATCH_SIZE = int(1e3)

  # Maximum number of jobs to enqueued before spawning a new scheduler.
  MAX_ENQUEUED_JOBS = 50

  def _execute(self):
    self._bq_setup()
    self._table.reload()
    page_token = self._params.get('bq_page_token', None)
    batch_size = self.BQ_BATCH_SIZE
    query_iterator = self.retry(self._table.fetch_data)(
        max_results=batch_size,
        page_token=page_token)

    enqueued_jobs_count = 0
    for query_page in query_iterator.pages:  # pylint: disable=unused-variable
      # Enqueue job for this page
      worker_params = self._params.copy()
      worker_params['bq_page_token'] = page_token
      worker_params['bq_batch_size'] = self.BQ_BATCH_SIZE
      self._enqueue(
        'BQToMeasurementProtocolProcessorGA4', worker_params, 0)
      enqueued_jobs_count += 1

      # Updates the page token reference for the next iteration.
      page_token = query_iterator.next_page_token

      # Spawns a new job to schedule the remaining pages.
      if (enqueued_jobs_count >= self.MAX_ENQUEUED_JOBS
          and page_token is not None):
        worker_params = self._params.copy()
        worker_params['bq_page_token'] = page_token
        self._enqueue(self.__class__.__name__, worker_params, 0)
        return


class BQToMeasurementProtocolProcessorGA4(BQWorker):
  """Worker pushing to Measurement Protocol for GA4 Properties."""

  def _send_payload_list(self, payloads):
    headers = {'content-type': 'application/json'}
    for payload in payloads:
      if self._debug:
        domain = 'https://www.google-analytics.com/debug/mp/collect'
        url = '{domain}?measurement_id={measurement_id}&api_secret={api_secret}'.format(
          domain=domain, measurement_id=self._measurement_id,
          api_secret=self._api_secret)
        response = requests.post(
          url,
          data=json.dumps(payload),
          headers=headers)
        result = json.loads(response.text)
        for msg in result['validationMessages']:
          self.log_warn('Validation Message: %s, Payload: %s' % (
            msg['description'], payload))
      else:
        domain = 'https://www.google-analytics.com/mp/collect'
        url = '{domain}?measurement_id={measurement_id}&api_secret={api_secret}'.format(
          domain=domain, measurement_id=self._measurement_id,
          api_secret=self._api_secret)
        response = requests.post(
          url,
          data=json.dumps(payload),
          headers=headers)
        if response.status_code != requests.codes.no_content:
          raise MeasurementProtocolException(
            'Failed to send event with status code (%s) and parameters: %s'
            % (response.status_code, payload))

  def _process_query_results(self, query_data, query_schema):
    """Sends event hits from query data."""
    fields = [f.name.encode('utf-8') for f in query_schema]
    payload_list = []
    for row in query_data:
      utf8_row = []
      for item in row:
        utf8_row.append(str(item).encode('utf-8'))
      template = self._params['template'] % dict(zip(fields, utf8_row))
      measurement_protocol_payload = json.loads(template)
      payload_list.append(measurement_protocol_payload)
      if len(payload_list) >= self._params['mp_batch_size']:
        self._send_payload_list(payload_list)
        payload_list = []
    if payload_list:
      # Sends remaining payloads.
      self._send_payload_list(payload_list)

  def _execute(self):
    self._bq_setup()
    self._table.reload()
    self._debug = self._params['debug']
    self._measurement_id = self._params['measurement_id']
    self._api_secret = self._params['api_secret']
    page_token = self._params['bq_page_token'] or None
    batch_size = self._params['bq_batch_size']
    query_iterator = self.retry(self._table.fetch_data)(
        max_results=batch_size,
        page_token=page_token)
    query_first_page = next(query_iterator.pages)
    self._process_query_results(query_first_page, query_iterator.schema)


class BQToMeasurementProtocol(BQWorker):
  """Worker to push data through Measurement Protocol."""

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('mp_batch_size', 'number', True, 20, ('Measurement Protocol batch size '
                                             '(https://goo.gl/7VeWuB)')),
      ('debug', 'boolean', True, False, 'Debug mode'),
  ]

  # BigQuery batch size for querying results. Default to 1000.
  BQ_BATCH_SIZE = int(1e3)

  # Maximum number of jobs to enqueued before spawning a new scheduler.
  MAX_ENQUEUED_JOBS = 50

  def _execute(self):
    self._bq_setup()
    self._table.reload()
    page_token = self._params.get('bq_page_token', None)
    batch_size = self.BQ_BATCH_SIZE
    query_iterator = self.retry(self._table.fetch_data)(
        max_results=batch_size,
        page_token=page_token)

    enqueued_jobs_count = 0
    for query_page in query_iterator.pages:  # pylint: disable=unused-variable
      # Enqueue job for this page
      worker_params = self._params.copy()
      worker_params['bq_page_token'] = page_token
      worker_params['bq_batch_size'] = self.BQ_BATCH_SIZE
      self._enqueue('BQToMeasurementProtocolProcessor', worker_params, 0)
      enqueued_jobs_count += 1

      # Updates the page token reference for the next iteration.
      page_token = query_iterator.next_page_token

      # Spawns a new job to schedule the remaining pages.
      if (enqueued_jobs_count >= self.MAX_ENQUEUED_JOBS
          and page_token is not None):
        worker_params = self._params.copy()
        worker_params['bq_page_token'] = page_token
        self._enqueue(self.__class__.__name__, worker_params, 0)
        return


class BQToMeasurementProtocolProcessor(BQWorker):
  """Worker pushing to Measurement Protocol the first page only of a query."""

  def _flatten(self, data):
    flat = False
    while not flat:
      flat = True
      for k in data.keys():
        if data[k] is None:
          del data[k]
        elif isinstance(data[k], list):
          for i, v in enumerate(data[k]):
            data['%s%i' % (k, i + 1)] = v
          del data[k]
          flat = False
        elif isinstance(data[k], dict):
          for l in data[k]:
            data['%s%s' % (k, l)] = data[k][l]
          del data[k]
          flat = False

  def _get_payload_from_data(self, data):
    self._flatten(data)
    payload = {'v': 1}  # Use version 1
    payload.update(data)
    return payload

  def _prepare_payloads_for_batch_request(self, payloads):
    """Merges payloads to send them in a batch request.

    Args:
        payloads: list of payload, each payload being a dictionary.

    Returns:
        Concatenated url-encoded payloads. For example:

          param1=value10&param2=value20
          param1=value11&param2=value21
    """
    assert isinstance(payloads, (list, tuple))
    payloads_utf8 = [sorted([(k, unicode(p[k]).encode('utf-8')) for k in p],
                            key=lambda t: t[0]) for p in payloads]
    return '\n'.join([urllib.urlencode(p) for p in payloads_utf8])

  def _send_batch_hits(self, batch_payload, user_agent='CRMint / 0.1'):
    """Sends a batch request to the Measurement Protocol endpoint.

    NB: Use the the HitBuilder service to validate a Measurement Protocol
        hit format with the Measurement Protocol Validation Server.

        https://ga-dev-tools.appspot.com/hit-builder/

    Args:
        batch_payload: list of payloads, each payload being a list of key/values
            tuples to pass to the Measurement Protocol batch endpoint.
        user_agent: string representing the client User Agent.

    Raises:
        MeasurementProtocolException: if the HTTP request fails.
    """
    headers = {'user-agent': user_agent}
    if self._debug:
      for payload in batch_payload.split('\n'):
        response = requests.post(
            'https://www.google-analytics.com/debug/collect',
            headers=headers,
            data=payload)
        result = json.loads(response.text)
        if (not result['hitParsingResult'] or
            not result['hitParsingResult'][0]['valid']):
          message = ('Invalid payload ("&" characters replaced with new lines):'
                     '\n\n%s\n\nValidation response:\n\n%s')
          readable_payload = payload.replace('&', '\n')
          self.log_warn(message, readable_payload, response.text)
    else:
      response = requests.post('https://www.google-analytics.com/batch',
                               headers=headers,
                               data=batch_payload)

      if response.status_code != requests.codes.ok:
        raise MeasurementProtocolException(
            'Failed to send event hit with status code (%s) and parameters: %s'
            % (response.status_code, batch_payload))

  def _send_payload_list(self, payload_list):
    batch_payload = self._prepare_payloads_for_batch_request(payload_list)
    try:
      self.retry(self._send_batch_hits, max_retries=1)(batch_payload)
    except MeasurementProtocolException as e:
      escaped_message = e.message.replace('%', '%%')
      self.log_error(escaped_message)

  def _process_query_results(self, query_data, query_schema):
    """Sends event hits from query data."""
    fields = [f.name for f in query_schema]
    payload_list = []
    for row in query_data:
      data = dict(zip(fields, row))
      payload = self._get_payload_from_data(data)
      payload_list.append(payload)
      if len(payload_list) >= self._params['mp_batch_size']:
        self._send_payload_list(payload_list)
        payload_list = []
    if payload_list:
      # Sends remaining payloads.
      self._send_payload_list(payload_list)

  def _execute(self):
    self._bq_setup()
    self._table.reload()
    self._debug = self._params['debug']
    page_token = self._params['bq_page_token'] or None
    batch_size = self._params['bq_batch_size']
    query_iterator = self.retry(self._table.fetch_data)(
        max_results=batch_size,
        page_token=page_token)
    query_first_page = next(query_iterator.pages)
    self._process_query_results(query_first_page, query_iterator.schema)


class BQMLTrainer(BQWorker):
  """Worker to run BQML SQL queries in BigQuery."""

  PARAMS = [
      ('query', 'sql', True, '', 'Query'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
  ]

  def _execute(self):
    client = self._get_client()
    job_name = '%i_%i_%s_%s' % (self._pipeline_id, self._job_id,
                                self.__class__.__name__, uuid.uuid4())
    job = client.run_async_query(job_name, self._params['query'])
    job.use_legacy_sql = False
    self._begin_and_wait(job)


class AWWorker(Worker):
  """Abstract AdWords API worker."""
  _MAX_ITEMS_PER_CALL = 10000

  GLOBAL_SETTINGS = ['google_ads_refresh_token', 'client_id', 'client_secret',
                     'developer_token']


  def _aw_setup(self):
    """Create AdWords API client."""
    # Throw exception if one or more AdWords global params are missing.
    for name in self.GLOBAL_SETTINGS:
      if not name in self._params or not self._params[name]:
        raise WorkerException(
            "One or more AdWords API global parameters are missing.")
    client_params_dict = {
        'adwords': {
            'client_customer_id': self._params['client_customer_id'].strip(),
            'developer_token': self._params['developer_token'].strip(),
            'client_id': self._params['client_id'].strip(),
            'client_secret': self._params['client_secret'].strip(),
            'refresh_token': self._params['google_ads_refresh_token'].strip(),
        }
    }
    client_params_yaml = yaml.safe_dump(client_params_dict, encoding='utf-8',
                                        allow_unicode=True)
    self._aw_client = adwords.AdWordsClient.LoadFromString(client_params_yaml)
    self._aw_client.cache = zeep.cache.InMemoryCache()


class BQToCM(AWWorker, BQWorker):
  """Customer Match worker."""

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('client_customer_id', 'string', True, '', 'Google Ads Customer ID'),
      ('list_name', 'string', True, '', 'Audience List Name'),
      ('upload_key_type', 'string', True, 'CONTACT_INFO',
       'Matching key type: CONTACT_INFO, CRM_ID, or MOBILE_ADVERTISING_ID'),
      ('app_id', 'string', False, '', 'Mobile application ID'),
      ('membership_life_span', 'number', True, 10000,
       'Membership Life Span, days'),
      ('remove_data', 'boolean', True, False,
       'Remove data from existing Audience List'),
  ]

  # BigQuery batch size for querying results. Default to 10000.
  BQ_BATCH_SIZE = int(10000)

  def _get_user_list(self, user_list_service):
    """Get or create the Customer Match list."""
    # Check if the list already exists.
    selector = {
        'fields': ['Name', 'Id'],
        'predicates': [{
            'field': 'Name',
            'operator': 'EQUALS',
            'values': self._params['list_name'],
        }],
    }
    result = user_list_service.get(selector)
    if result['entries']:
      user_list = result['entries'][0]
      self.log_info('User list "%s" with ID = %d was found.',
                    user_list['name'], user_list['id'])
      return user_list['id']
    # The list doesn't exist, have to create one.
    user_list = {
        'xsi_type': 'CrmBasedUserList',
        'name': self._params['list_name'],
        'description': 'This is a list of users created by CRMint',
        'membershipLifeSpan': self._params['membership_life_span'],
        'uploadKeyType': self._params['upload_key_type'],
    }
    if self._params['upload_key_type'] == 'MOBILE_ADVERTISING_ID':
      user_list['appId'] = self._params['app_id']
    # Create an operation to add the user list.
    operations = [{'operator': 'ADD', 'operand': user_list}]
    result = user_list_service.mutate(operations)
    user_list = result['value'][0]
    self.log_info('The user list "%s" with ID = %d has been created.',
                  user_list['name'], user_list['id'])
    return user_list['id']

  def _process_page(self, page_data):
    """Upload data fetched from BigQuery table to the Customer Match list."""

    def remove_nones(obj):
      """Remove all None and empty dict values from a dict recursively."""
      if not isinstance(obj, dict):
        return obj
      clean_obj = {}
      for k in obj:
        v = remove_nones(obj[k])
        if v is not None:
          clean_obj[k] = v
      return clean_obj if clean_obj else None

    members = [remove_nones(row[0]) for row in page_data]
    user_list_service = self._aw_client.GetService('AdwordsUserListService',
                                                   'v201809')
    user_list_id = self._get_user_list(user_list_service)
    # Flow control to keep calls within usage limits.
    self.log_info('Starting upload.')
    for i in range(0, len(members), self._MAX_ITEMS_PER_CALL):
      members_to_upload = members[i:i + self._MAX_ITEMS_PER_CALL]
      mutate_members_operation = {
          'operand': {
              'userListId': user_list_id,
              'membersList': members_to_upload,
          },
      }
      if self._params["remove_data"]:
        mutate_members_operation['operator'] = 'REMOVE'
        operation_string = 'removed from'
      else:
        mutate_members_operation['operator'] = 'ADD'
        operation_string = 'added to'
      response = user_list_service.mutateMembers([mutate_members_operation])
      if 'userLists' in response:
        user_list = response['userLists'][0]
        self.log_info(
            '%d members were %s user list "%s" with ID = %d.',
            len(members_to_upload), operation_string, user_list['name'],
            user_list['id'])

  def _execute(self):
    self._aw_setup()
    self._bq_setup()
    self._table.reload()
    page_token = self._params.get('bq_page_token', None)
    page_iterator = self.retry(self._table.fetch_data)(
        max_results=self.BQ_BATCH_SIZE,
        page_token=page_token)
    page = next(page_iterator.pages)
    self._process_page(page)
    # Update the page token reference for the next iteration.
    page_token = page_iterator.next_page_token
    if page_token:
      self._params['bq_page_token'] = page_token
      self._enqueue(self.__class__.__name__, self._params, 0)


class BQToAppConversionAPI(BQWorker):
  """Worker that sends app conversions to App Conversion Tracking API."""

  PARAMS = [
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
  ]
  GLOBAL_SETTINGS = ['app_conversion_api_developer_token']
  CONTENT_TYPE = 'application/json; charset=utf-8'
  HEADER_PARAMS = ['User_Agent', 'X_Forwarded_For']
  BODY_PARAM = 'app_event_data'
  REQUIRED_PARAMS = ['rdid', 'id_type', 'lat', 'app_version', 'os_version',
                     'sdk_version', 'timestamp', 'link_id', 'app_event_type']
  OPTIONAL_PARAMS = ['value', 'app_event_name', 'currency_code', 'gclid']
  API_URL = 'https://www.googleadservices.com/pagead/conversion/app/1.0'
  # BigQuery batch size for querying results. Default to 10000.
  BQ_BATCH_SIZE = int(10000)

  def _send_api_requests(self, headers, params, body=None):
    """Sends app conversion and cross-network attribution requests."""
    response = requests.post(self.API_URL, headers=headers, params=params,
                             json=body)
    if response.status_code != requests.codes.ok:
      self.log_warn(
          'Failed to send app conversion request, status code %s.\n'
          '  Headers: %s\n  Parameters: %s\n  Body: %s'
          % (response.status_code, headers, params, body)
      )
      return
    result = json.loads(response.text)
    if not result['attributed']:
      self.log_warn(
          'App conversion was not attributed to Google Ads.\n'
          '  Headers: %s\n  Parameters: %s\n  Body: %s\n  Errors: %s'
          % (headers, params, body, result['errors'])
      )
      return

    self.log_info(
        'App conversion was attributed to Google Ads.\n'
        '  Headers: %s\n  Parameters: %s\n  Body: %s\n  Errors: %s'
        % (headers, params, body, result['errors'])
    )

    params['ad_event_id'] = result['ad_events'][0]['ad_event_id']
    params['attributed'] = 1
    response = requests.post('%s/cross_network' % self.API_URL,
                             headers=headers, params=params, json=body)
    if response.status_code != requests.codes.ok:
      self.log_warn(
          'Failed to send cross-network attribution request, status code %s.\n'
          '  Headers: %s\n  Parameters: %s\n  Body: %s'
          % (response.status_code, headers, params, body)
      )

  def _process_page(self, page, fields):
    """Send each row of a BQ table page as a single app conversion."""
    for values in page:
      row = dict(zip(fields, values))
      headers = {'Content-Type': self.CONTENT_TYPE}
      for param in self.HEADER_PARAMS:
        if row[param] is not None:
          headers[param.replace('_', '-')] = row[param]
        else:
          self.log_warn(
              'Missing value for the required header "%s" in table "%s.%s"' % (
                  param.replace('_', '-'), self._params['bq_dataset_id'],
                  self._params['bq_table_id']))
      params = {'dev_token': self._params['app_conversion_api_developer_token']}
      for param in self.REQUIRED_PARAMS:
        if row[param] is not None:
          params[param] = row[param]
        else:
          self.log_warn(
              'Missing value for the required param "%s" in table "%s.%s"' % (
                  param, self._params['bq_dataset_id'],
                  self._params['bq_table_id']))
      for param in self.OPTIONAL_PARAMS:
        if param in row and row[param] is not None:
          params[param] = row[param]
      if self.BODY_PARAM in row and row[self.BODY_PARAM] is not None:
        body = {self.BODY_PARAM: row[self.BODY_PARAM]}
      else:
        body = None
        headers['Content-Length'] = '0'

      self._send_api_requests(headers, params, body)

  def _execute(self):
    """Fetch a BQ table page, process it, schedule self for the next page."""
    if not self._params.get('app_conversion_api_developer_token'):
      raise WorkerException('App Conversion API developer token is not '
                            'specified in General Settings.')
    self._bq_setup()
    self._table.reload()
    page_token = self._params.get('bq_page_token', None)
    page_iterator = self.retry(self._table.fetch_data)(
        max_results=self.BQ_BATCH_SIZE,
        page_token=page_token)
    fields = [field.name for field in page_iterator.schema]
    for param in self.REQUIRED_PARAMS + self.HEADER_PARAMS:
      if param not in fields:
        raise WorkerException(
            'Required field "%s" not found in table "%s.%s"' % (
                param, self._params['bq_dataset_id'],
                self._params['bq_table_id']))
    page = next(page_iterator.pages)
    self._process_page(page, fields)
    # Update the page token reference for the next iteration.
    page_token = page_iterator.next_page_token
    if page_token:
      self._params['bq_page_token'] = page_token
      self._enqueue(self.__class__.__name__, self._params, 0)


class AutoMLWorker(Worker):
  """Abstract AutoML worker."""

  def _get_automl_client(self, location):
    """Constructs a Resource for interacting with the AutoML API."""
    # Use the location-appropriate AutoML endpoint
    # Otherwise, API calls fail with HttpError 400
    if location == 'eu':
      endpoint = 'eu-automl'
    else:  # global: us-central1, etc
      endpoint = 'automl'
    api_endpoint = 'https://{}.googleapis.com'.format(endpoint)
    self.log_info('Using AutoML client with endpoint: %s', api_endpoint)

    # You might be wondering why we're using the discovery-based Google API
    # client library as opposed to the more modern Google Cloud client library.
    # The reason is that the modern client libraries (e.g. google-cloud-automl)
    # are not supported on App Engine's Python 2 runtime.
    # See: https://github.com/googleapis/google-cloud-python
    client_options = {'api_endpoint': api_endpoint}
    credentials = ServiceAccountCredentials.from_json_keyfile_name(_KEY_FILE)
    return build(endpoint, 'v1beta1', credentials=credentials, client_options=client_options)

  @staticmethod
  def _get_automl_parent_name(project, location):
    """Constructs the parent location path."""
    return "projects/{project}/locations/{location}".format(
        project=project,
        location=location,
    )

  @staticmethod
  def _get_full_model_name(project, location, model):
    """Constructs the fully-qualified name for the given AutoML model."""
    return "{parent}/models/{model}".format(
        parent=AutoMLWorker._get_automl_parent_name(project, location),
        model=model,
    )

  @staticmethod
  def _get_full_dataset_name(project, location, dataset):
    """Constructs the fully-qualified name for the given AutoML dataset."""
    return "{parent}/datasets/{dataset}".format(
        parent=AutoMLWorker._get_automl_parent_name(project, location),
        dataset=dataset,
    )

  @staticmethod
  def _build_display_name(name, strftime_format):
    """ Constructs an strftime formatted display name"""
    display_name = name
    if strftime_format:
      strftime = datetime.now().strftime(strftime_format)
      display_name += strftime
    return display_name

  @staticmethod
  def _get_latest_dataset_id(client, parent, display_name):
    """Finds the latest dataset matching the given name"""
    response = client.projects().locations().datasets() \
                     .list(parent=parent).execute()

    for dataset in response['datasets']:
      if dataset['displayName'] == display_name:
        return dataset['name'].split('/')[-1]
    else:
      raise WorkerException('Dataset with given name was not found: %s' % display_name)

  @staticmethod
  def _get_latest_model_id(client, parent, display_name):
    """Finds the latest model matching the given name"""
    response = client.projects().locations().models() \
                     .list(parent=parent).execute()

    for model in response['model']:
      if model['displayName'] == display_name:
        return model['name'].split('/')[-1]
    else:
      raise WorkerException('Model with given name was not found: %s' % display_name)


class AutoMLPredictor(AutoMLWorker):
  """Worker to run AutoML batch prediction jobs."""

  PARAMS = [
      ('model_project_id', 'string', True, '', 'AutoML Project ID'),
      ('model_location', 'string', True, '', 'AutoML Model Location'),
      ('model_id', 'string', False, '', 'AutoML Model ID'),
      ('model_name', 'string', False, '', 'AutoML Model Name'),
      ('strftime_format', 'string', False, '', 'AutoML Model strftime format'),
      ('input_bq_uri', 'string', False, '',
       'Input - BigQuery Table URI (e.g. bq://projectId.dataset.table)'),
      ('input_gcs_uri', 'string', False, '',
       'Input - Cloud Storage CSV URI (e.g. gs://bucket/directory/file.csv)'),
      ('output_bq_project_uri', 'string', False, '',
       'Output - BigQuery Project URI (e.g. bq://projectId)'),
      ('output_gcs_uri_prefix', 'string', False, '',
       'Output - Cloud Storage output directory (e.g. gs://bucket/directory)'),
  ]

  def _execute(self):
    model_location = self._params['model_location']
    parent = self._get_automl_parent_name(self._params['model_project_id'],
                                          model_location)

    client = self._get_automl_client(location=model_location)

    model_id = self._get_model_id(client, parent)

    # Construct the fully-qualified model name and config for the prediction.
    model_name = self._get_full_model_name(self._params['model_project_id'],
                                           model_location,
                                           model_id)
    body = {
        'inputConfig': self._generate_input_config(),
        'outputConfig': self._generate_output_config()
    }

    # Launch the prediction and retrieve its operation name so we can track it.
    self.log_info('Launching batch prediction job @ %s: %s', parent, body)
    client = self._get_automl_client(location=model_location)
    response = client.projects().locations().models() \
                     .batchPredict(name=model_name, body=body).execute()
    self.log_info('Launched batch prediction job: %s', response)

    # Since the batch prediction might take more than the 10 minutes the job
    # service has to serve a response to the Push Queue, we can't wait on it
    # here. We thus spawn a worker that waits until the operation is completed.
    operation_name = response.get('name')
    waiter_params = {'operation_name': operation_name, 'location': model_location}
    self._enqueue('AutoMLWaiter', waiter_params, 5 * 60)

  def _generate_input_config(self):
    """Constructs the input configuration for the batch prediction request."""
    input_bq_uri = self._params['input_bq_uri']
    input_gcs_uri = self._params['input_gcs_uri']

    if input_bq_uri and not input_gcs_uri:
      return {'bigquery_source': {'input_uri': input_bq_uri}}
    elif input_gcs_uri and not input_bq_uri:
      return {'gcs_source': {'input_uris': [input_gcs_uri]}}
    else:
      raise WorkerException('Provide either a BigQuery or GCS source.')

  def _generate_output_config(self):
    """Constructs the output configuration for the batch prediction request."""
    output_bq_project_uri = self._params['output_bq_project_uri']
    output_gcs_uri_prefix = self._params['output_gcs_uri_prefix']

    if output_bq_project_uri and not output_gcs_uri_prefix:
      return {'bigquery_destination': {'output_uri': output_bq_project_uri}}
    elif output_gcs_uri_prefix and not output_bq_project_uri:
      return {'gcs_destination': {'output_uri_prefix': output_gcs_uri_prefix}}
    else:
      raise WorkerException('Provide either a BigQuery or GCS destination.')

  def _get_model_id(self, client, parent):
    model_id = self._params['model_id']
    model_name = self._params['model_name']
    strftime_format = self._params['strftime_format']

    if model_id and not (model_name and strftime_format):
      self.log_info('Using Model with ID: %s', model_id)
    elif (model_name and strftime_format) and not model_id:
      model_display_name = self._build_display_name(model_name, strftime_format)
      self.log_info('Searching for Model name matching: %s', model_display_name)
      model_id = self._get_latest_model_id(client, parent, model_display_name)
      self.log_info('Found Model with ID: %s', model_id)
    else:
      raise WorkerException('Provide either a Model ID or name & strftime format.')
    return model_id


class AutoMLWaiter(AutoMLWorker):
  """Worker that keeps respawning until an AutoML operation is completed."""

  def _execute(self):
    client = self._get_automl_client(location=self._params['location'])
    operation_name = self._params['operation_name']

    response = client.projects().locations().operations() \
                     .get(name=operation_name).execute()

    if response.get('done'):
      if response.get('error'):
        raise WorkerException('AutoML operation failed: %s' % response)
      else:
        self.log_info('AutoML operation completed successfully: %s', response)
    else:
      self.log_info('AutoML operation still running: %s', response)
      self._enqueue('AutoMLWaiter', self._params, self._params.get('delay', 10 * 60))


class AutoMLImporter(AutoMLWorker):
  """Worker to create AutoML datasets by importing data from Bigquery or GCS."""

  PARAMS = [
    ('dataset_project_id', 'string', True, '', 'AutoML Project ID'),
    ('dataset_location', 'string', True, '', 'AutoML Dataset Location'),
    ('dataset_name', 'string', True, '', 'Dataset Name'),
    ('strftime_format', 'string', False, '', 'strftime format (appended to name for uniqueness)'),
    ('dataset_metadata', 'text', False, '', 'Dataset metadata in JSON'),
    ('input_bq_uri', 'string', False, '',
      'Input - BigQuery Table URI (e.g. bq://projectId.dataset.table)'),
    ('input_gcs_uri', 'string', False, '',
      'Input - Cloud Storage CSV URI (e.g. gs://bucket/directory/file.csv)'),
  ]

  def _execute(self):
    dataset_location = self._params['dataset_location']
    display_name = self._build_display_name(self._params['dataset_name'],
                                            self._params['strftime_format'])

    parent = self._get_automl_parent_name(self._params['dataset_project_id'],
                                          dataset_location)

    dataset_metadata = self._params['dataset_metadata']
    if dataset_metadata:
      metadata = json.loads(dataset_metadata)
    else:
      metadata = {}

    body = {
      'displayName': display_name,
      'tablesDatasetMetadata': metadata
    }

    # Launch the dataset creation and retrieve the fully qualified name.
    self.log_info('Launching dataset creation job @ %s: %s', parent, body)
    client = self._get_automl_client(location=dataset_location)
    response = client.projects().locations().datasets() \
                     .create(parent=parent, body=body).execute()
    self.log_info('Launched dataset creation job: %s', response)

    dataset_name = response.get('name')

    self.log_info('Created dataset at: %s', dataset_name)

    body = {
      'inputConfig': self._generate_input_config()
    }

    # Launch the data import and retrieve its operation name so we can track it.
    self.log_info('Launching data import job @ %s: %s', parent, body)
    client = self._get_automl_client(location=dataset_location)
    response = client.projects().locations().datasets() \
                     .importData(name=dataset_name, body=body).execute()
    self.log_info('Launched data import job: %s', response)

    # Since the data import might take more than the 10 minutes the job
    # service has to serve a response to the Push Queue, we can't wait on it
    # here. We thus spawn a worker that waits until the operation is completed.
    operation_name = response.get('name')
    waiter_params = {
      'operation_name': operation_name,
      'delay': 15 * 60,
      'location': dataset_location,
    }
    self._enqueue('AutoMLWaiter', waiter_params, 15 * 60)

  def _generate_input_config(self):
    """Constructs the input configuration for the data import request."""
    input_bq_uri = self._params['input_bq_uri']
    input_gcs_uri = self._params['input_gcs_uri']

    if input_bq_uri and not input_gcs_uri:
      return {'bigquery_source': {'input_uri': input_bq_uri}}
    elif input_gcs_uri and not input_bq_uri:
      return {'gcs_source': {'input_uris': [input_gcs_uri]}}
    else:
      raise WorkerException('Provide either a BigQuery or GCS source.')


class AutoMLTrainer(AutoMLWorker):
  """Worker to train AutoML models."""

  PARAMS = [
      ('model_project_id', 'string', True, '', 'AutoML Project ID'),
      ('model_location', 'string', True, '', 'AutoML Model Location'),
      ('model_name', 'string', True, '', 'AutoML Model Name'),
      ('model_strftime_format', 'string', False, '', 'strftime format (appended to name for uniqueness)'),
      ('dataset_id', 'string', False, '', 'AutoML Dataset ID'),
      ('dataset_name', 'string', False, '', 'AutoML Dataset Name'),
      ('dataset_strftime_format', 'string', False, '', 'AutoML Dataset strftime format'),
      ('training_columns', 'string_list', False, '', 'Training Column names (else, all are used)'),
      ('target_column', 'string', True, '', 'Target Column name'),
      ('optimization_objective', 'string', False, '', 'Optimization objective'),
      ('training_budget', 'number', True, '', 'Training budget (in hours)'),
      ('stop_early', 'boolean', True, False, 'Stop training early (if possible)'),
  ]

  def _execute(self):
    model_location = self._params['model_location']
    display_name = self._build_display_name(self._params['model_name'],
                                            self._params['model_strftime_format'])

    parent = self._get_automl_parent_name(self._params['model_project_id'],
                                          model_location)

    client = self._get_automl_client(location=model_location)

    dataset_id = self._get_dataset_id(client, parent)
    dataset_resource_name = self._get_full_dataset_name(self._params['model_project_id'],
                                                        model_location,
                                                        dataset_id)

    column_specs = self._get_column_specs(client, dataset_resource_name)

    target_column_spec = self._get_column_spec(column_specs, self._params['target_column'])
    self._set_target_column(client, dataset_resource_name, target_column_spec)

    training_columns = filter(None, map(lambda column: column.strip(),
                                        self._params['training_columns']))
    training_columns_specs = map(
      lambda column: self._get_column_spec(column_specs, column), training_columns)

    body = {
      'displayName': display_name,
      'datasetId': dataset_id,
      'tablesModelMetadata': self._generate_model_metadata(target_column_spec,
                                                           training_columns_specs)
    }

    # Launch the prediction and retrieve its operation name so we can track it.
    self.log_info('Launching model training job @ %s: %s', parent, body)
    response = client.projects().locations().models() \
                     .create(parent=parent, body=body).execute()
    self.log_info('Launched model training job: %s', response)

    # Since the model training might take more than the 10 minutes the job
    # service has to serve a response to the Push Queue, we can't wait on it
    # here. We thus spawn a worker that waits until the operation is completed.
    operation_name = response.get('name')
    waiter_params = {
      'operation_name': operation_name,
      'delay': self._params['training_budget'] * 60 * 30,
      'location': model_location,
    }
    self._enqueue('AutoMLWaiter', waiter_params, 15 * 60)

  def _generate_model_metadata(self, target_column_spec, training_columns_specs):
    model_metadata = {
      'targetColumnSpec': {'name': target_column_spec},
      'trainBudgetMilliNodeHours': self._params['training_budget'] * 1000,
      'disableEarlyStopping': not self._params['stop_early']
    }

    if len(training_columns_specs) > 0:
      model_metadata['inputFeatureColumnSpecs'] = map(lambda cid: {'name': cid},
                                                      training_columns_specs)

    if self._params['optimization_objective']:
      model_metadata['optimizationObjective'] = self._params['optimization_objective']

    return model_metadata

  def _get_dataset_id(self, client, parent):
    dataset_id = self._params['dataset_id']
    dataset_name = self._params['dataset_name']
    dataset_strftime_format = self._params['dataset_strftime_format']

    if dataset_id and not (dataset_name and dataset_strftime_format):
      self.log_info('Using dataset with ID: %s', dataset_id)
    elif (dataset_name and dataset_strftime_format) and not dataset_id:
      dataset_display_name = self._build_display_name(dataset_name, dataset_strftime_format)
      self.log_info('Searching for dataset name matching: %s', dataset_display_name)
      dataset_id = self._get_latest_dataset_id(client, parent, dataset_display_name)
      self.log_info('Found dataset with ID: %s', dataset_id)
    else:
      raise WorkerException('Provide either a Dataset ID or name & strftime format.')
    return dataset_id

  def _get_column_specs(self, client, dataset_resource_name):
    response = client.projects().locations().datasets() \
                     .get(name=dataset_resource_name).execute()

    table_spec_id = response['tablesDatasetMetadata']['primaryTableSpecId']
    table_resource_name = '{parent}/tableSpecs/{table}'.format(parent=dataset_resource_name,
                                                               table=table_spec_id)

    response = client.projects().locations().datasets().tableSpecs().columnSpecs() \
                     .list(parent=table_resource_name).execute()
    return response['columnSpecs']

  def _get_column_spec(self, column_specs, column):
    for column_spec in column_specs:
      if column_spec['displayName'] == column:
        return column_spec['name']
    else:
      raise WorkerException('Column with given name not found: %s' % column)

  def _set_target_column(self, client, dataset_resource_name, target_column_spec):
    body = {
      'tablesDatasetMetadata': {'targetColumnSpecId': target_column_spec.split('/')[-1]}
    }
    # Set target column for dataset
    self.log_info('Modifying target column for dataset: %s', body)
    response = client.projects().locations().datasets() \
                     .patch(name=dataset_resource_name, body=body).execute()
    self.log_info('Modified target column for dataset: %s', response)
