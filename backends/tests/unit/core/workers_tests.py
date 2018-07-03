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

import os
import unittest

from apiclient.errors import HttpError
import cloudstorage
from google.appengine.ext import testbed
from google.cloud.bigquery.query import QueryResults
from google.cloud.exceptions import ClientError
import mock

from core import workers


class TestAbstractWorker(unittest.TestCase):

  def setUp(self):
    super(TestAbstractWorker, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_taskqueue_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestAbstractWorker, self).tearDown()
    self.testbed.deactivate()

  @mock.patch('core.logging.logger')
  def test_log_info_succeeds(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_info('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'INFO')

  @mock.patch('core.logging.logger')
  def test_log_warn_succeeds(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_warn('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'WARNING')

  @mock.patch('core.logging.logger')
  def test_log_error_succeeds(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_error('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'ERROR')

  @mock.patch('core.logging.logger')
  def test_execute_client_error_raises_worker_exception(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    class DummyWorker(workers.Worker):
      def _execute(self):
        raise ClientError('There has been an issue here.')
    worker = DummyWorker({}, 1, 1)
    with self.assertRaises(workers.WorkerException):
      worker.execute()

  def test_enqueue_succeedly_add_to_the_list(self):
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(len(worker._workers_to_enqueue), 0)
    worker._enqueue('DummyClass', 'params')
    self.assertEqual(len(worker._workers_to_enqueue), 1)
    self.assertEqual(worker._workers_to_enqueue[0][0], 'DummyClass')
    self.assertEqual(worker._workers_to_enqueue[0][1], 'params')

  @mock.patch('time.sleep')
  @mock.patch('core.logging.logger')
  def test_retry_until_a_finite_number_of_times(self, patched_logger,
      patched_time_sleep):
    patched_logger.log_struct.__name__ = 'foo'
    # NB: bypass the time.sleep wait, otherwise the test will take ages
    patched_time_sleep.side_effect = lambda delay: delay
    worker = workers.Worker({}, 1, 1)
    def _raise_value_error_exception(*args, **kwargs):
      raise ValueError('Wrong value.')
    fake_request = mock.Mock()
    fake_request.__name__ = 'foo'
    fake_request.side_effect = _raise_value_error_exception
    with self.assertRaises(ValueError):
      worker.retry(fake_request)()
    self.assertGreaterEqual(fake_request.call_count, 2)

  def test_retry_raises_error_if_bad_request_error(self):
    worker = workers.Worker({}, 1, 1)
    def _raise_value_error_exception(*args, **kwargs):
      raise HttpError(mock.Mock(status=400), '')
    fake_request = mock.Mock()
    fake_request.__name__ = 'foo'
    fake_request.side_effect = _raise_value_error_exception
    with self.assertRaises(HttpError):
      worker.retry(fake_request)()
    self.assertEqual(fake_request.call_count, 1)


class TestBQWorker(unittest.TestCase):

  @mock.patch('time.sleep')
  @mock.patch('google.cloud.bigquery.job.QueryJob')
  def test_begin_and_wait_start_jobs(self, patched_bigquery_QueryJob,
      patched_time_sleep):
    # NB: bypass the time.sleep wait, otherwise the test will take ages
    patched_time_sleep.side_effect = lambda delay: delay
    worker = workers.BQWorker({}, 1, 1)
    job0 = patched_bigquery_QueryJob()
    job0.begin.side_effect = lambda: True
    def _mark_as_done():
      job0.state = 'DONE'
    job0.reload.side_effect = _mark_as_done
    job0.error_result = None
    worker._begin_and_wait(job0)
    job0.begin.assert_called_once()

  @mock.patch('time.sleep')
  @mock.patch('google.cloud.bigquery.job.QueryJob')
  @mock.patch('core.workers.BQWorker._enqueue')
  def test_begin_and_wait_enqueue_bqwaiter_after_some_time(self,
      patched_BQWorker_enqueue, patched_bigquery_QueryJob, patched_time_sleep):
    # NB: bypass the time.sleep wait, otherwise the test will take ages
    patched_time_sleep.side_effect = lambda delay: delay
    def _fake_enqueue(*args, **kwargs):
      # Do Nothing
      return True
    patched_BQWorker_enqueue.side_effect = _fake_enqueue
    worker = workers.BQWorker({'bq_project_id': 'BQID'}, 1, 1)
    job0 = patched_bigquery_QueryJob()
    job0.error_result = None
    worker._begin_and_wait(job0)
    patched_BQWorker_enqueue.assert_called_once()
    self.assertEqual(patched_BQWorker_enqueue.call_args[0][0], 'BQWaiter')
    self.assertIsInstance(patched_BQWorker_enqueue.call_args[0][1], dict)


class TestBQWaiter(unittest.TestCase):

  def test_execute_enqueue_job_if_done(self):
    patcher_get_client = mock.patch.object(workers.BQWaiter, '_get_client',
        return_value=None)
    self.addCleanup(patcher_get_client.stop)
    patcher_get_client.start()
    mockAsyncJob = mock.Mock()
    mockAsyncJob.error_result = None
    patcher_async_job = mock.patch('google.cloud.bigquery.job._AsyncJob',
        return_value=mockAsyncJob)
    self.addCleanup(patcher_async_job.stop)
    patcher_async_job.start()
    patcher_worker_enqueue = mock.patch('core.workers.BQWaiter._enqueue')
    self.addCleanup(patcher_worker_enqueue.stop)
    patched_enqueue = patcher_worker_enqueue.start()
    worker = workers.BQWaiter(
        {
            'bq_project_id': 'BQID',
            'job_names': ['Job1', 'Job2'],
        },
        1,
        1)
    worker._client = mock.Mock()
    worker._execute()
    patched_enqueue.assert_called_once()
    self.assertEqual(patched_enqueue.call_args[0][0], 'BQWaiter')


class TestStorageToBQImporter(unittest.TestCase):

  def setUp(self):
    super(TestStorageToBQImporter, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_urlfetch_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()
    self.testbed.init_blobstore_stub()
    self.testbed.init_datastore_v3_stub()

    patcher_listbucket = mock.patch('cloudstorage.listbucket')
    patched_listbucket = patcher_listbucket.start()
    self.addCleanup(patcher_listbucket.stop)
    def _fake_listbucket(bucket_prefix):
      filenames = [
        'input.csv',
        'subdir/input.csv',
        'data.csv',
        'subdir/data.csv',
      ]
      for suffix in filenames:
        filename = os.path.join(bucket_prefix, suffix)
        stat = cloudstorage.GCSFileStat(
            filename,
            0,
            '686897696a7c876b7e',
            0)
        yield stat
    patched_listbucket.side_effect = _fake_listbucket

  def tearDown(self):
    super(TestStorageToBQImporter, self).tearDown()
    self.testbed.deactivate()

  def test_get_source_uris_succeeds(self):
    worker = workers.StorageToBQImporter(
      {
        'source_uris': [
          'gs://bucket/data.csv',
          'gs://bucket/subdir/data.csv',
        ]
      },
      1,
      1)
    source_uris = worker._get_source_uris()
    self.assertEqual(len(source_uris), 2)
    self.assertEqual(source_uris[0], 'gs://bucket/data.csv')
    self.assertEqual(source_uris[1], 'gs://bucket/subdir/data.csv')

  def test_get_source_uris_with_pattern(self):
    worker = workers.StorageToBQImporter(
      {
        'source_uris': [
          'gs://bucket/subdir/*.csv',
        ]
      },
      1,
      1)
    source_uris = worker._get_source_uris()
    self.assertEqual(len(source_uris), 2)
    self.assertEqual(source_uris[0], 'gs://bucket/subdir/input.csv')
    self.assertEqual(source_uris[1], 'gs://bucket/subdir/data.csv')


class TestBQToMeasurementProtocol(unittest.TestCase):

  def setUp(self):
    super(TestBQToMeasurementProtocol, self).setUp()

    self._client = mock.Mock()
    patcher_get_client = mock.patch.object(
        workers.BQToMeasurementProtocol,
        '_get_client',
        return_value=self._client)
    self.addCleanup(patcher_get_client.stop)
    patcher_get_client.start()

    patcher_requests_post = mock.patch('requests.post')
    self.addCleanup(patcher_requests_post.stop)
    self._patched_post = patcher_requests_post.start()

    self._worker = workers.BQToMeasurementProtocol(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
        },
        1,
        1)

  def _use_query_results(self, response_json):
    # NB: be sure to remove the jobReference from the api response used to
    #     create the QueryResults instance.
    response_json_copy = response_json.copy()
    del response_json_copy['jobReference']
    fake_query_results = QueryResults.from_api_repr(response_json_copy, self._client)
    self._client.run_sync_query.return_value = fake_query_results
    self._client._connection.api_request.return_value = response_json

  def test_success_with_one_post_request(self):
    self._use_query_results({
        'jobReference': {
            'jobId': 'one-row-query',
        },
        'rows': [
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 'event'},
                    {'v': 1},
                    {'v': 'category'},
                    {'v': 'action'},
                    {'v': 'label'},
                    {'v': 'value'},
                    {'v': 'User Agent / 1.0'},
                ]
            }
        ],
        'schema': {
            'fields': [
                {'name': 'tid', 'type': 'STRING'},
                {'name': 'cid', 'type': 'STRING'},
                {'name': 't', 'type': 'STRING'},
                {'name': 'ni', 'type': 'FLOAT'},
                {'name': 'ec', 'type': 'STRING'},
                {'name': 'ea', 'type': 'STRING'},
                {'name': 'el', 'type': 'STRING'},
                {'name': 'ev', 'type': 'STRING'},
                {'name': 'ua', 'type': 'STRING'},
            ]
        }
    })

    mock_response = mock.Mock()
    mock_response.status_code = 200
    self._patched_post.return_value = mock_response

    self._worker._execute()
    self._patched_post.assert_called_once()
    self.assertEqual(
        self._patched_post.call_args[0][0],
        'https://www.google-analytics.com/collect')
    self.assertEqual(
        self._patched_post.call_args[1],
        {
            'headers': {'user-agent': 'CRMint / 0.1'},
            'data': {
                'ni': 1.0,
                'el': 'label',
                'cid': '35009a79-1a05-49d7-b876-2b884d0f825b',
                'ea': 'action',
                'ec': 'category',
                't': 'event',
                'v': 1,
                'tid': 'UA-12345-1',
                'ev': 'value',
                'ua': 'User Agent / 1.0'
            }
        })

  @mock.patch('core.logging.logger')
  @mock.patch('time.sleep')
  def test_log_exception_if_http_fails(self, patched_time_sleep, patched_logger):
    # Bypass the time.sleep wait
    patched_time_sleep.return_value = 1
    # NB: patching the StackDriver logger is needed because there is no
    #     testbed service available for now
    patched_logger.log_struct.__name__ = 'foo'
    patched_logger.log_struct.return_value = "patched_log_struct"
    self._use_query_results({
        'jobReference': {
            'jobId': 'one-row-query',
        },
        'rows': [
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 'event'},
                    {'v': 1},
                    {'v': 'category'},
                    {'v': 'action'},
                    {'v': 'label'},
                    {'v': 'value'},
                    {'v': 'User Agent / 1.0'},
                ]
            }
        ],
        'schema': {
            'fields': [
                {'name': 'tid', 'type': 'STRING'},
                {'name': 'cid', 'type': 'STRING'},
                {'name': 't', 'type': 'STRING'},
                {'name': 'ni', 'type': 'FLOAT'},
                {'name': 'ec', 'type': 'STRING'},
                {'name': 'ea', 'type': 'STRING'},
                {'name': 'el', 'type': 'STRING'},
                {'name': 'ev', 'type': 'STRING'},
                {'name': 'ua', 'type': 'STRING'},
            ]
        }
    })

    mock_response = mock.Mock()
    mock_response.status_code = 500
    self._patched_post.return_value = mock_response

    self._worker._execute()
    # Called 6 times because of retry.
    self.assertEqual(self._patched_post.call_count, 6)
    # When retry stops it should log the message as an error.
    patched_logger.log_error.called_once()
