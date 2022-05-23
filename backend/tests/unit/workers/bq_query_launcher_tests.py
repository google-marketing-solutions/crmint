"""Tests for bq_query_launcher."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials
from google.cloud import bigquery

from jobs.workers.bigquery import bq_query_launcher


def _make_credentials():
  return mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)


class BQQueryLauncherTest(parameterized.TestCase):

  @parameterized.named_parameters(
      ('Overwrites table', True, bigquery.WriteDisposition.WRITE_TRUNCATE),
      ('Appends to table', False, bigquery.WriteDisposition.WRITE_APPEND),
  )
  def test_append_rows_to_existing_table(self, overwrite, write_disposition):
    worker_inst = bq_query_launcher.BQQueryLauncher(
        {
            'job_id': 'JOBID',
            'query': 'SELECT * FROM mytable',
            'bq_project_id': 'PROJECT',
            'bq_dataset_id': 'DATASET',
            'bq_table_id': 'output_table',
            'bq_dataset_location': 'EU',
            'overwrite': overwrite,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    bq_client = bigquery.Client(
        project='PROJECT', credentials=_make_credentials())
    mock_job = mock.create_autospec(
        bigquery.job.QueryJob, instance=True, spec_set=True)
    mock_job.error_result = None
    mock_job.state = 'RUNNING'
    patched_query = self.enter_context(
        mock.patch.object(
            bq_client, 'query', autospec=True, return_value=mock_job))
    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    self.enter_context(
        mock.patch.object(
            worker_inst, '_get_client', autospec=True, return_value=bq_client))
    worker_inst.execute()
    call_job_config = patched_query.call_args.kwargs['job_config']
    self.assertIsInstance(call_job_config, bigquery.QueryJobConfig)
    with self.subTest('Ensures query is passed with standard SQL config'):
      patched_query.assert_called_once_with(
          'SELECT * FROM mytable',
          job_id_prefix='1_1_BQQueryLauncher',
          location='EU',
          job_config=mock.ANY)
      self.assertFalse(call_job_config.use_legacy_sql,
                       msg='We only support the standard SQL for this worker')
    with self.subTest('Storage of results has been configured'):
      # Unset `create_disposition` will default to CREATE_IF_NEEDED
      self.assertIsNone(call_job_config.create_disposition)
      self.assertEqual(call_job_config.write_disposition, write_disposition)
      self.assertEqual(
          call_job_config.destination,
          bigquery.TableReference.from_string('DATASET.output_table',
                                              'PROJECT'))


if __name__ == '__main__':
  absltest.main()
