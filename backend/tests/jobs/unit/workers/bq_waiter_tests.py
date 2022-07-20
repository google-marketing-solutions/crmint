"""Tests for bq_waiter."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials
from google.cloud import bigquery

from jobs.workers import worker
from jobs.workers.bigquery import bq_waiter


def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


class BQWaiterTest(parameterized.TestCase):

  @parameterized.parameters(
      {'job_status': 'RUNNING', 'enqueue_called': True,},
      {'job_status': 'DONE', 'enqueue_called': False,},
  )
  def test_execute_job_with_status(self, job_status, enqueue_called):
    logging_creds = {
        'logger_project': 'PROJECT',
        'logger_credentials': _make_credentials(),
    }
    worker_inst = bq_waiter.BQWaiter(
        {'job_id': 'JOBID',}, 1, 1, **logging_creds)
    mock_job = mock.create_autospec(
        bigquery.job.QueryJob, instance=True, spec_set=True)
    mock_job.error_result = None
    mock_job.state = job_status
    mock_client = mock.create_autospec(
        bigquery.Client, instance=True, spec_set=True)
    mock_client.get_job.return_value = mock_job
    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_client',
            return_value=mock_client,
            autospec=True,
            spec_set=True))
    patched_enqueue = self.enter_context(
        mock.patch.object(
            worker_inst,
            '_enqueue',
            autospec=True,
            spec_set=True))
    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    worker_inst._execute()
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
      mock_client = mock.create_autospec(
          bigquery.Client, instance=True, spec_set=True)
      mock_client.get_job.return_value = mock_job
      self.enter_context(
          mock.patch.object(
              bq_waiter.BQWaiter,
              '_get_client',
              return_value=mock_client,
              autospec=True,
              spec_set=True))
      worker_inst = bq_waiter.BQWaiter(
          {'job_id': 'JOBID',}, 1, 1,
          logger_project='PROJECT',
          logger_credentials=_make_credentials())
      worker_inst._execute()


if __name__ == '__main__':
  absltest.main()
