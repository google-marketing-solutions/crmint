"""Tests for bq_worker."""

from unittest import mock
import os

from absl.testing import absltest
from absl.testing import parameterized

from google.auth import credentials
from google.cloud import bigquery
from google.api_core.client_info import ClientInfo

from jobs.workers import worker
from jobs.workers.bigquery import bq_worker


def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


class BQWorkerTest(parameterized.TestCase):

  @parameterized.parameters(
      {'job_is_done': False, 'enqueue_called': True,},
      {'job_is_done': True, 'enqueue_called': False,},
  )
  def test_enqueues_bqwaiter_after_some_time(self, job_is_done, enqueue_called):
    # Mocks `time.sleep` to speed up the tests.
    self.enter_context(
        mock.patch(
            'time.sleep',
            side_effect=lambda delay: delay,
            autospec=True,
            spec_set=True))
    logging_creds = {
        'logger_project': 'PROJECT',
        'logger_credentials': _make_credentials(),
    }
    worker_inst = bq_worker.BQWorker(
        {'bq_project_id': 'BQID'}, 1, 1, **logging_creds)
    mock_client = mock.create_autospec(
        bigquery.Client, instance=True, spec_set=False)
    mock_client.project = 'PROJECT'
    job = bigquery.job.QueryJob('JOBID', 'query', mock_client)
    self.enter_context(
        mock.patch.object(job, 'done', return_value=job_is_done, autospec=True))
    patched_enqueue = self.enter_context(
        mock.patch.object(
            worker_inst,
            '_enqueue',
            return_value=True,
            autospec=True,
            spec_set=True))
    worker_inst._wait(job)
    if enqueue_called:
      patched_enqueue.assert_called_once()
      self.assertEqual(patched_enqueue.call_args[0][0], 'BQWaiter')
      self.assertEqual(patched_enqueue.call_args[0][1], {'job_id': 'JOBID'})
    else:
      patched_enqueue.assert_not_called()

  def test_job_error_raises_worker_exception(self):
    with self.assertRaisesRegex(worker.WorkerException, 'Custom Message'):
      mock_job = mock.create_autospec(
          bigquery.job.QueryJob, instance=True, spec_set=True)
      mock_job.error_result = {'message': 'Custom Message'}
      mock_job.state = 'DONE'
      worker_inst = bq_worker.BQWorker(
          {'bq_project_id': 'BQID'}, 1, 1,
          logger_project='PROJECT',
          logger_credentials=_make_credentials())
      worker_inst._wait(mock_job)

  def test_generates_proper_bq_table_name_from_params(self):
    params = {
      'bq_project_id': 'a_project',
      'bq_dataset_id': 'a_dataset_id',
      'bq_table_id': 'a_table_id'
    }

    worker = bq_worker.BQWorker(params, 0, 0)

    self.assertEqual('a_project.a_dataset_id.a_table_id',
                     worker._generate_qualified_bq_table_name())

class BQWorkerGetClientTest(parameterized.TestCase):

  @parameterized.parameters(
      {
        'report_usage_id_present': True,
        'client_info_user_agent': 'cloud-solutions/crmint-usage-v3',
      },
      {
        'report_usage_id_present': False, 
        'client_info_user_agent': None
      },
  )
  def test_get_client_handles_report_usage_id(
      self, report_usage_id_present, client_info_user_agent):
    report_usage_id = 'some-usage-id' if report_usage_id_present else ''
    with (
        mock.patch.dict(
            os.environ,
            {'REPORT_USAGE_ID': report_usage_id}
            if report_usage_id_present
            else {},
        ),
        mock.patch('os.getenv', return_value=report_usage_id) as getenv_mock,
        mock.patch('google.cloud.bigquery.Client') as client_mock,
    ):
      worker_inst = bq_worker.BQWorker({}, 0, 0)
      worker_inst._get_client()

      if report_usage_id_present:
        getenv_mock.assert_called_with('REPORT_USAGE_ID')
      else:
        getenv_mock.assert_not_called()

      client_mock.assert_called_once()
      _, kwargs = client_mock.call_args
      if report_usage_id_present:
        self.assertIsInstance(kwargs['client_info'], ClientInfo)
        self.assertEqual(
          kwargs['client_info'].user_agent, client_info_user_agent
        )
      else:
        self.assertIsNone(kwargs.get('client_info'))


if __name__ == '__main__':
  absltest.main()
