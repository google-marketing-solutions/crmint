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
from google.cloud.bigquery.dataset import Dataset
from google.cloud.bigquery.table import Table
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
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestAbstractWorker, self).tearDown()
    self.testbed.deactivate()

  def test_default_params_values(self):
    class DummyWorker(workers.Worker):
      PARAMS = [
        ('int_with_default', 'number', True, 20, 'Description'),
      ]
    worker = DummyWorker({}, 1, 1)
    self.assertIsInstance(worker._params['int_with_default'], int)
    self.assertEqual(worker._params['int_with_default'], 20)

  @mock.patch('core.cloud_logging.logger')
  def test_log_info_succeeds(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_info('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'INFO')

  @mock.patch('core.cloud_logging.logger')
  def test_log_warn_succeeds(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_warn('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'WARNING')

  @mock.patch('core.cloud_logging.logger')
  def test_log_error_succeeds(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    worker = workers.Worker({}, 1, 1)
    self.assertEqual(patched_logger.log_struct.call_count, 0)
    worker.log_error('Hi there!')
    self.assertEqual(patched_logger.log_struct.call_count, 1)
    call_first_arg = patched_logger.log_struct.call_args[0][0]
    self.assertEqual(call_first_arg.get('log_level'), 'ERROR')

  @mock.patch('core.cloud_logging.logger')
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
  @mock.patch('core.cloud_logging.logger')
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


class TestBQToMeasurementProtocolMixin(object):

  def _use_query_results(self, response_json):
    # NB: be sure to remove the jobReference from the api response used to
    #     create the Table instance.
    response_json_copy = response_json.copy()
    del response_json_copy['jobReference']
    mock_dataset = mock.Mock()
    mock_dataset._client = self._client
    mock_table = Table('mock_table', mock_dataset)
    self._client._connection.api_request.return_value = response_json
    self._client.dataset.return_value = mock_dataset
    mock_dataset.table.return_value = mock_table


class TestBQToMeasurementProtocolProcessor(TestBQToMeasurementProtocolMixin, unittest.TestCase):

  def setUp(self):
    super(TestBQToMeasurementProtocolProcessor, self).setUp()

    self._client = mock.Mock()
    patcher_get_client = mock.patch.object(
        workers.BQToMeasurementProtocolProcessor,
        '_get_client',
        return_value=self._client)
    self.addCleanup(patcher_get_client.stop)
    patcher_get_client.start()

    patcher_requests_post = mock.patch('requests.post')
    self.addCleanup(patcher_requests_post.stop)
    self._patched_post = patcher_requests_post.start()
    self.maxDiff = None  # This is to see full diff when self.assertEqual fails.

  @mock.patch('time.sleep')
  def test_success_with_one_post_request(self, patched_time_sleep):
    # Bypass the time.sleep wait
    patched_time_sleep.return_value = 1
    self._worker = workers.BQToMeasurementProtocolProcessor(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'bq_batch_size': 10,
            'mp_batch_size': 20,
            'debug': False,
        },
        1,
        1)
    self._use_query_results({
        'tableReference': {
            'tableId': 'mock_table',
        },
        'jobReference': {
            'jobId': 'two-rows-query',
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
                    {'v': 0.9},
                    {'v': 'User Agent / 1.0'},
                    {'v': None},
                ]
            },
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 'event'},
                    {'v': 1},
                    {'v': 'category'},
                    {'v': 'action'},
                    {'v': u'\u043c\u0435\u0442\u043a\u0430'},
                    {'v': 0.8},
                    {'v': 'User Agent / 1.0'},
                    {'v': 'segment1'},
                ]
            }
        ],
        'schema': {
            'fields': [
                {'name': 'tid', 'type': 'STRING'},
                {'name': 'cid', 'type': 'STRING'},
                {'name': 't', 'type': 'STRING'},
                {'name': 'ni', 'type': 'INTEGER'},
                {'name': 'ec', 'type': 'STRING'},
                {'name': 'ea', 'type': 'STRING'},
                {'name': 'el', 'type': 'STRING'},
                {'name': 'ev', 'type': 'FLOAT'},
                {'name': 'ua', 'type': 'STRING'},
                {'name': 'cd1', 'type': 'STRING'},
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
        'https://www.google-analytics.com/batch')
    self.assertEqual(
        self._patched_post.call_args[1],
        {
            'headers': {'user-agent': 'CRMint / 0.1'},
            'data':
"""cid=35009a79-1a05-49d7-b876-2b884d0f825b&ea=action&ec=category&el=label&ev=0.9&ni=1&t=event&tid=UA-12345-1&ua=User+Agent+%2F+1.0&v=1
cd1=segment1&cid=35009a79-1a05-49d7-b876-2b884d0f825b&ea=action&ec=category&el=%D0%BC%D0%B5%D1%82%D0%BA%D0%B0&ev=0.8&ni=1&t=event&tid=UA-12345-1&ua=User+Agent+%2F+1.0&v=1""",
        })

  @mock.patch('time.sleep')
  def test_success_with_enhanced_ecommerce_request(self, patched_time_sleep):
    # Bypass the time.sleep wait
    patched_time_sleep.return_value = 1
    self._worker = workers.BQToMeasurementProtocolProcessor(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'bq_batch_size': 10,
            'mp_batch_size': 20,
            'debug': False,
        },
        1,
        1)
    self._use_query_results({
        'tableReference': {
            'tableId': 'mock_table',
        },
        'jobReference': {
            'jobId': 'one-row-with-array-of-structs-query',
        },
        'rows': [
            {
                'f': [
                    {'v': 'UA-12345-6'},  # tid
                    {'v': '123456789.1234567890'},  # cid
                    {'v': 'pageview'},  # t
                    {'v': 'purchase'},  # pa
                    {'v': '987654321'},  # ti
                    {'v': 'Moscow'},  # ta
                    {'v': '1540.0'},  # tr
                    {'v': 'RUB'},  # cu
                    {
                        'v': [  # pr
                            {
                                'v': {  # pr1
                                    'f': [
                                        {'v': 'SKU1'},  # pr1id
                                        {'v': 'Product1'},  # pr1nm
                                        {'v': 'Brand1'},  # pr1br
                                        {'v': 'Cat1'},  # pr1ca
                                        {'v': '110.0'},  # pr1pr
                                        {'v': '1'}  # pr1qt
                                    ]
                                }
                            },
                            {
                                'v': {  # pr2
                                    'f': [
                                        {'v': 'SKU2'},  # pr2id
                                        {'v': 'Product2'},  # pr2nm
                                        {'v': 'Brand2'},  # pr2br
                                        {'v': 'Cat2'},  # pr2ca
                                        {'v': '220.0'},  # pr2pr
                                        {'v': '2'}  # pr2qt
                                    ]
                                }
                            },
                            {
                                'v': {  # pr3
                                    'f': [
                                        {'v': 'SKU3'},  # pr3id
                                        {'v': 'Product3'},  # pr3nm
                                        {'v': 'Brand3'},  # pr3br
                                        {'v': 'Cat3'},  # pr3ca
                                        {'v': '330.0'},  # pr3pr
                                        {'v': '3'}  # pr3qt
                                    ]
                                }
                            }
                        ]
                    },
                    {
                        'v': [  # il
                            {  # il1
                                'v': {
                                    'f': [
                                        {'v': 'List1'},  # il1nm
                                        {
                                            'v': [  # il1pi
                                                {
                                                    'v': {  # il1pi1
                                                        'f': [
                                                            {'v': 'SKU11'},  # il1pi1id
                                                            {'v': 'Product11'},  # il1pi1nm
                                                            {'v': 'Brand11'},  # il1pi1br
                                                            {'v': 'Cat11'},  # il1pi1ca
                                                            {'v': '1110.0'}  # il1pi1pr
                                                        ]
                                                    }
                                                },
                                                {
                                                    'v': {  # il1pi2
                                                        'f': [
                                                            {'v': 'SKU12'},  # il1pi2id
                                                            {'v': 'Product12'},  # il1pi2nm
                                                            {'v': 'Brand12'},  # il1pi2br
                                                            {'v': 'Cat12'},  # il1pi2ca
                                                            {'v': '1220.0'}  # il1pi2pr
                                                        ]
                                                    }
                                                },
                                                {
                                                    'v': {  # il1pi3
                                                        'f': [
                                                            {'v': 'SKU13'},  # il1pi3id
                                                            {'v': 'Product13'},  # il1pi3nm
                                                            {'v': 'Brand13'},  # il1pi3br
                                                            {'v': 'Cat13'},  # il1pi3ca
                                                            {'v': '1330.0'}  # il1pi3pr
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                }
                            },
                            {  # il2
                                'v': {
                                    'f': [
                                        {'v': 'List2'},  # il2nm
                                        {
                                            'v': [  # il2pi
                                                {
                                                    'v': {  # il2pi1
                                                        'f': [
                                                            {'v': 'SKU21'},  # il2pi1id
                                                            {'v': 'Product21'},  # il2pi1nm
                                                            {'v': 'Brand21'},  # il2pi1br
                                                            {'v': 'Cat21'},  # il2pi1ca
                                                            {'v': '2110.0'}  # il2pi1pr
                                                        ]
                                                    }
                                                },
                                                {
                                                    'v': {  # il2pi2
                                                        'f': [
                                                            {'v': 'SKU22'},  # il2pi2id
                                                            {'v': 'Product22'},  # il2pi2nm
                                                            {'v': 'Brand22'},  # il2pi2br
                                                            {'v': None},  # il2pi2ca
                                                            {'v': '2220.0'}  # il2pi2pr
                                                        ]
                                                    }
                                                },
                                                {
                                                    'v': {  # il2pi3
                                                        'f': [
                                                            {'v': 'SKU23'},  # il2pi3id
                                                            {'v': 'Product23'},  # il2pi3nm
                                                            {'v': 'Brand23'},  # il2pi3br
                                                            {'v': 'Cat23'},  # il2pi3ca
                                                            {'v': '2330.0'}  # il2pi3pr
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        ],
        'schema': {
            'fields': [
                {'name': 'tid', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 'cid', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 't', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 'pa', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 'ti', 'type': 'INTEGER', 'mode': 'NULLABLE'},
                {'name': 'ta', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 'tr', 'type': 'FLOAT', 'mode': 'NULLABLE'},
                {'name': 'cu', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 'pr', 'type': 'RECORD', 'mode': 'REPEATED', 'fields': [
                    {'name': 'id', 'type': 'STRING', 'mode': 'NULLABLE'},
                    {'name': 'nm', 'type': 'STRING', 'mode': 'NULLABLE'},
                    {'name': 'br', 'type': 'STRING', 'mode': 'NULLABLE'},
                    {'name': 'ca', 'type': 'STRING', 'mode': 'NULLABLE'},
                    {'name': 'pr', 'type': 'FLOAT', 'mode': 'NULLABLE'},
                    {'name': 'qt', 'type': 'INTEGER', 'mode': 'NULLABLE'}
                ]},
                {'name': 'il', 'type': 'RECORD', 'mode': 'REPEATED', 'fields': [
                    {'name': 'nm', 'type': 'STRING', 'mode': 'NULLABLE'},
		    {'name': 'pi', 'type': 'RECORD', 'mode': 'REPEATED', 'fields': [
			{'name': 'id', 'type': 'STRING', 'mode': 'NULLABLE'},
			{'name': 'nm', 'type': 'STRING', 'mode': 'NULLABLE'},
			{'name': 'br', 'type': 'STRING', 'mode': 'NULLABLE'},
			{'name': 'ca', 'type': 'STRING', 'mode': 'NULLABLE'},
			{'name': 'pr', 'type': 'FLOAT', 'mode': 'NULLABLE'}
		    ]},
                ]}
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
        'https://www.google-analytics.com/batch')
    self.assertEqual(
        self._patched_post.call_args[1],
        {
            'headers': {'user-agent': 'CRMint / 0.1'},
            'data': 'cid=123456789.1234567890&cu=RUB&il1nm=List1&il1pi1br=Brand11&il1pi1ca=Cat11&il1pi1id=SKU11&il1pi1nm=Product11&il1pi1pr=1110.0&il1pi2br=Brand12&il1pi2ca=Cat12&il1pi2id=SKU12&il1pi2nm=Product12&il1pi2pr=1220.0&il1pi3br=Brand13&il1pi3ca=Cat13&il1pi3id=SKU13&il1pi3nm=Product13&il1pi3pr=1330.0&il2nm=List2&il2pi1br=Brand21&il2pi1ca=Cat21&il2pi1id=SKU21&il2pi1nm=Product21&il2pi1pr=2110.0&il2pi2br=Brand22&il2pi2id=SKU22&il2pi2nm=Product22&il2pi2pr=2220.0&il2pi3br=Brand23&il2pi3ca=Cat23&il2pi3id=SKU23&il2pi3nm=Product23&il2pi3pr=2330.0&pa=purchase&pr1br=Brand1&pr1ca=Cat1&pr1id=SKU1&pr1nm=Product1&pr1pr=110.0&pr1qt=1&pr2br=Brand2&pr2ca=Cat2&pr2id=SKU2&pr2nm=Product2&pr2pr=220.0&pr2qt=2&pr3br=Brand3&pr3ca=Cat3&pr3id=SKU3&pr3nm=Product3&pr3pr=330.0&pr3qt=3&t=pageview&ta=Moscow&ti=987654321&tid=UA-12345-6&tr=1540.0&v=1'
        })

  @mock.patch('core.cloud_logging.logger')
  @mock.patch('time.sleep')
  def test_log_exception_if_http_fails(self, patched_time_sleep, patched_logger):
    # Bypass the time.sleep wait
    patched_time_sleep.return_value = 1
    # NB: patching the StackDriver logger is needed because there is no
    #     testbed service available for now
    patched_logger.log_struct.__name__ = 'foo'
    patched_logger.log_struct.return_value = "patched_log_struct"
    self._worker = workers.BQToMeasurementProtocolProcessor(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'bq_batch_size': 10,
            'mp_batch_size': 20,
            'debug': False,
        },
        1,
        1)
    self._use_query_results({
        'tableReference': {
            'tableId': 'mock_table',
        },
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
                {'name': 'ni', 'type': 'INTEGER'},
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
    # Called 2 times because of 1 retry.
    self.assertEqual(self._patched_post.call_count, 2)
    # When retry stops it should log the message as an error.
    patched_logger.log_error.called_once()


class TestBQToMeasurementProtocol(TestBQToMeasurementProtocolMixin, unittest.TestCase):

  def setUp(self):
    super(TestBQToMeasurementProtocol, self).setUp()

    self._client = mock.Mock()
    patcher_get_client = mock.patch.object(
        workers.BQToMeasurementProtocol,
        '_get_client',
        return_value=self._client)
    self.addCleanup(patcher_get_client.stop)
    patcher_get_client.start()

  @mock.patch('time.sleep')
  def test_success_with_spawning_new_worker(self, patched_time_sleep):
    # Bypass the time.sleep wait
    patched_time_sleep.return_value = 1
    self._worker = workers.BQToMeasurementProtocol(
        {
            'bq_project_id': 'BQID',
            'bq_dataset_id': 'DTID',
            'bq_table_id': 'table_id',
            'bq_page_token': None,
            'mp_batch_size': 20,
        },
        1,
        1)
    self._worker.MAX_ENQUEUED_JOBS = 1
    api_response = {
        'tableReference': {
            'tableId': 'mock_table',
        },
        'jobReference': {
            'jobId': 'one-row-query',
        },
        'pageToken': 'abc',
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
                    {'v': 0.9},
                    {'v': 'User Agent / 1.0'},
                ]
            },
            {
                'f': [
                    {'v': 'UA-12345-1'},
                    {'v': '35009a79-1a05-49d7-b876-2b884d0f825b'},
                    {'v': 'event'},
                    {'v': 1},
                    {'v': 'category'},
                    {'v': 'action'},
                    {'v': 'label'},
                    {'v': 0.8},
                    {'v': 'User Agent / 1.0'},
                ]
            },
        ],
        'schema': {
            'fields': [
                {'name': 'tid', 'type': 'STRING'},
                {'name': 'cid', 'type': 'STRING'},
                {'name': 't', 'type': 'STRING'},
                {'name': 'ni', 'type': 'INTEGER'},
                {'name': 'ec', 'type': 'STRING'},
                {'name': 'ea', 'type': 'STRING'},
                {'name': 'el', 'type': 'STRING'},
                {'name': 'ev', 'type': 'FLOAT'},
                {'name': 'ua', 'type': 'STRING'},
            ]
        }
    }
    self._use_query_results(api_response)

    patcher_worker_enqueue = mock.patch.object(workers.BQToMeasurementProtocol, '_enqueue')
    self.addCleanup(patcher_worker_enqueue.stop)
    patched_enqueue = patcher_worker_enqueue.start()
    def _remove_next_page_token(worker_name, *args, **kwargs):
      if worker_name == 'BQToMeasurementProtocol':
        del api_response['pageToken']
        self._use_query_results(api_response)
    patched_enqueue.side_effect = _remove_next_page_token

    self._worker._execute()
    self.assertEqual(patched_enqueue.call_count, 2)
    self.assertEqual(patched_enqueue.call_args_list[0][0][0], 'BQToMeasurementProtocolProcessor')
    self.assertEqual(patched_enqueue.call_args_list[0][0][1]['bq_page_token'], None)
    self.assertEqual(patched_enqueue.call_args_list[1][0][0], 'BQToMeasurementProtocol')
    self.assertEqual(patched_enqueue.call_args_list[1][0][1]['bq_page_token'], 'abc')
