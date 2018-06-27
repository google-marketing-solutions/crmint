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
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_info('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'INFO')

  @mock.patch('core.logging.logger')
  def test_log_warn_succeeds(self, patched_logger):
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_warn('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'WARNING')

  @mock.patch('core.logging.logger')
  def test_log_error_succeeds(self, patched_logger):
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_error('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'ERROR')

  @mock.patch('core.logging.logger')
  def test_execute_client_error_raises_worker_exception(self, patched_logger):
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
    worker._get_source_uris()
    self.assertEqual(len(worker._source_uris), 2)
    self.assertEqual(worker._source_uris[0], 'gs://bucket/data.csv')
    self.assertEqual(worker._source_uris[1], 'gs://bucket/subdir/data.csv')

  def test_get_source_uris_with_pattern(self):
    worker = workers.StorageToBQImporter(
      {
        'source_uris': [
          'gs://bucket/subdir/*.csv',
        ]
      },
      1,
      1)
    worker._get_source_uris()
    self.assertEqual(len(worker._source_uris), 2)
    self.assertEqual(worker._source_uris[0], 'gs://bucket/subdir/input.csv')
    self.assertEqual(worker._source_uris[1], 'gs://bucket/subdir/data.csv')
