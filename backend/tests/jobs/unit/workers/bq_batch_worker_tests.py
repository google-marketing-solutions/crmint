"""Tests for bq_batch_worker.py"""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from google.api_core import page_iterator
from google.cloud import bigquery

from jobs.workers.bigquery import bq_batch_worker


class MockImplBatchWorker(bq_batch_worker.BQBatchDataWorker):
  def _get_sub_worker_name(self) -> str:
    return "sub_worker_name"


class BQBatchDataWorkerTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    self.setup_mock_bq_client()

  def setup_mock_bq_client(self):
    self.mock_row_iterator = mock.Mock(spec=bigquery.table.RowIterator)
    self.mock_row_iterator.pages = iter([])
    self.mock_row_iterator.next_page_token = None

    self.mock_bq_table = mock.Mock(spec=bigquery.table.Table)

    self.mock_bq_client = mock.Mock(spec=bigquery.Client)
    self.mock_bq_client.list_rows.return_value = self.mock_row_iterator
    self.mock_bq_client.get_table.return_value = self.mock_bq_table

    self.patched_bq_client_init = self.enter_context(
      mock.patch.object(bigquery, 'Client', autospec=True))
    self.patched_bq_client_init.return_value = self.mock_bq_client

  def test_loads_data_from_table_provided_in_params(self):
    """Batch worker loads data from the provided BQ table"""
    params = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id'
    }
    worker = MockImplBatchWorker(params, 0, 0)
    worker._execute()

    self.mock_bq_client.get_table.assert_called_with(
      'a_project.a_dataset_id.a_table_id'
    )

  def test_loads_table_with_provided_table_name_in_params(self):
    """Batch workers loads the table using the provided name in the params."""
    params = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': 'a_token'
    }
    worker = MockImplBatchWorker(params, 0, 0)
    worker._execute()

    self.mock_bq_client.get_table.assert_called_with(
      'a_project.a_dataset_id.a_table_id'
    )

  def test_loads_data_with_page_token_provided_in_params(self):
    """Batch worker loads data using the provided page token."""
    params = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': 'a_token'
    }
    worker = MockImplBatchWorker(params, 0, 0)
    worker._execute()

    self.mock_bq_client.list_rows.assert_called_with(
      table=self.mock_bq_table,
      page_token='a_token',
      page_size=mock.ANY
    )

  @mock.patch('jobs.workers.worker.Worker._enqueue')
  def test_enqueues_sub_worker_for_every_page_of_results(self, mocked_enqueue):
    """Batch worker enqueues a sub_worker for every page of results."""
    params = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': 'a_token'
    }
    self.mock_row_iterator.next_page_token = 'next_token'
    self.mock_row_iterator.pages = iter(['results_page_1', 'results_page_2'])

    worker = MockImplBatchWorker(params, 0, 0)
    worker._execute()

    expected_params_first_page = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': 'a_token',
      'bq_batch_size': 1000
    }
    expected_params_second_page = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': 'next_token',
      'bq_batch_size': 1000
    }
    calls = [
      mock.call('sub_worker_name', expected_params_first_page),
      mock.call('sub_worker_name', expected_params_second_page),
    ]

    mocked_enqueue.assert_has_calls(calls)

  @mock.patch('jobs.workers.worker.Worker._enqueue')
  def test_enqueues_new_parent_worker_if_too_many_sub_workers_enqueued(
    self, mocked_enqueue
  ):
    """Batch worker enqueues a new parent worker if too many sub workers were
    enqueued.
    """
    params = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': 'a_token'
    }
    self.mock_row_iterator.next_page_token = 'next_token'
    self.mock_row_iterator.pages = iter(['results_page_1',
                                         'results_page_2',
                                         'results_page_3',
                                         'results_page_4'])

    # Temp patch max sub-workers to enqueue with new value.  Simply setting
    # it will cause other tests to fail
    with mock.patch('jobs.workers.bigquery.bq_batch_worker.BQBatchDataWorker.MAX_ENQUEUED_JOBS_PER_COORDINATOR',
                    new_callable=mock.PropertyMock
                    ) as max_enqueued_property:
      max_enqueued_property.return_value = 1
      worker = MockImplBatchWorker(params, 0, 0)
      worker._execute()

    expected_params_sub_worker = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': 'a_token',
      'bq_batch_size': 1000
    }
    expected_params_new_parent_worker = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': 'next_token',
    }

    calls = [
      mock.call('sub_worker_name', expected_params_sub_worker),
      mock.call('MockImplBatchWorker', expected_params_new_parent_worker),
    ]
    mocked_enqueue.assert_has_calls(calls)


class MockImplTablePageResultsProcessorWorker(bq_batch_worker.TablePageResultsProcessorWorker):
  was_called: bool = False
  was_called_with = None

  def _process_page_results(self, page_data: page_iterator.Page) -> None:
    self.was_called = True
    self.was_called_with = page_data


class TablePageResultsProcessorWorkerTests(parameterized.TestCase):
  def setUp(self):
    super().setUp()
    self.setup_mock_bq_client()

  def setup_mock_bq_client(self):
    self.mock_row_iterator = mock.Mock(spec=bigquery.table.RowIterator)
    self.mock_row_iterator.pages = iter(['results_1', 'results_2'])
    self.mock_row_iterator.next_page_token = 'the_next_token'

    self.mock_bq_table = mock.Mock(spec=bigquery.table.Table)

    self.mock_bq_client = mock.Mock(spec=bigquery.Client)
    self.mock_bq_client.list_rows.return_value = self.mock_row_iterator
    self.mock_bq_client.get_table.return_value = self.mock_bq_table

    self.patched_bq_client_init = self.enter_context(
      mock.patch.object(bigquery, 'Client', autospec=True))
    self.patched_bq_client_init.return_value = self.mock_bq_client

  @parameterized.parameters(
    {'page_token_value': '',
     'batch_size_value': 100,
     'expected_err': 'Param \'bq_page_token\' needs to be set for batch processing.',},
    {'page_token_value': 'a_token',
     'batch_size_value': None,
     'expected_err': 'Param \'bq_batch_size\' needs to be set for batch processing.',},
  )
  def test_fails_execution_if_required_parameters_are_missing(
    self,
    page_token_value,
    batch_size_value,
    expected_err
  ):
    """Results processor fails if the BQ table to process param is missing."""
    params = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_page_token': page_token_value,
      'bq_batch_size': batch_size_value
    }
    worker = MockImplTablePageResultsProcessorWorker(params, 0, 0)
    with self.assertRaises(ValueError) as ctx:
      worker._execute()

    self.assertEqual(expected_err, str(ctx.exception))

  def test_loads_data_from_table_provided_in_params(self):
    """Batch worker loads data from the provided BQ table"""
    params = {
      'bq_page_token': 'a_token',
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_batch_size': 10
    }
    worker = MockImplTablePageResultsProcessorWorker(params, 0, 0)
    worker._execute()

    self.mock_bq_client.get_table.assert_called_with(
      'a_project.a_dataset_id.a_table_id'
    )

  def test_loads_data_with_values_provided_in_params(self):
    """Batch worker loads data using the provided page token."""
    params = {
      'bq_page_token': 'a_token',
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_batch_size': 10
    }
    worker = MockImplTablePageResultsProcessorWorker(params, 0, 0)
    worker._execute()

    self.mock_bq_client.list_rows.assert_called_with(
      table=self.mock_bq_table,
      page_token='a_token',
      page_size=10
    )

  def test_calls_process_page_results(self):
    params = {
      'bq_page_token': 'a_token',
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id',
      'bq_batch_size': 10
    }
    worker = MockImplTablePageResultsProcessorWorker(params, 0, 0)
    worker._execute()

    self.assertTrue(worker.was_called)
    self.assertEqual(worker.was_called_with, 'results_1')


if __name__ == '__main__':
  absltest.main()
