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
import json
import os
from random import random
import time
import urllib
import uuid

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaIoBaseUpload
import cloudstorage as gcs
from oauth2client.service_account import ServiceAccountCredentials
import requests
from google.cloud import bigquery
from google.cloud.exceptions import ClientError


_KEY_FILE = os.path.join(os.path.dirname(__file__), '..', 'data',
                         'service-account.json')
AVAILABLE = (
    'BQMLTrainer',
    'BQQueryLauncher',
    'BQToMeasurementProtocol',
    'BQToStorageExporter',
    'Commenter',
    'GAAudiencesUpdater',
    'GADataImporter',
    'GAToBQImporter',
    'MLPredictor',
    'StorageChecker',
    'StorageCleaner',
    'StorageToBQImporter',
)

# Defines how many times to retry on failure, default to 5 times.
DEFAULT_MAX_RETRIES = os.environ.get('MAX_RETRIES', 5)


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

  # Maximum number of execution attempts.
  MAX_ATTEMPTS = 3

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
        except Exception as e:  # pylint: disable=broad-except
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
      raise WorkerException( 'Files matching the patterns are too small')



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
  ]

  def _get_source_uris(self):
    stats = self._get_matching_stats(self._params['source_uris'])
    return ['gs:/%s' % s.filename for s in stats]

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
    self.log_info('%i rows of data fetched for %s', rows_fetched, log_str)

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


class MLWorker(Worker):
  """Abstract ML Engine worker."""

  def _get_ml_client(self):
    self._ml_client = build('ml', 'v1')

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


class MeasurementProtocolException(WorkerException):
  """Measurement Protocol execution exception."""
  pass


class MeasurementProtocolWorker(Worker):
  """Abstract Measurement Protocol worker."""

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
    assert isinstance(payloads, list) or isinstance(payloads, tuple)
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
    query_iterator = self.retry(self._table.fetch_data, max_retries=1)(
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


class BQToMeasurementProtocolProcessor(BQWorker, MeasurementProtocolWorker):
  """Worker pushing to Measurement Protocol the first page only of a query."""

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
    query_iterator = self.retry(self._table.fetch_data, max_retries=1)(
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
