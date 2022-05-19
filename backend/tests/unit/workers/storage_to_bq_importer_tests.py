"""Tests for storage_to_bq_importer."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials
from google.cloud import bigquery
from google.cloud import storage

from jobs.workers.bigquery import storage_to_bq_importer


def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


class StorageToBQImporterTest(parameterized.TestCase):

  @parameterized.named_parameters(
      {
          'testcase_name': 'CSV with no overwrite',
          # Worker parameters
          'import_json': False,
          'rows_to_skip': 0,
          'autodetect': True,
          'schema': None,
          'overwrite': False,
          'dont_create': True,
          # Resulting job config
          'job_config_source_format': None,
          'job_config_skip_leading_rows': 0,
          'job_config_write_disposition': 'WRITE_APPEND',
          'job_config_create_disposition': 'CREATE_NEVER'
      },
      {
          'testcase_name': 'CSV with overwrite',
          # Worker parameters
          'import_json': False,
          'rows_to_skip': 2,
          'autodetect': False,
          'schema': None,
          'overwrite': True,
          'dont_create': False,
          # Resulting job config
          'job_config_source_format': None,
          'job_config_skip_leading_rows': 2,
          'job_config_write_disposition': 'WRITE_TRUNCATE',
          'job_config_create_disposition': 'CREATE_IF_NEEDED'
      },
      {
          'testcase_name': 'JSON with overwrite',
          # Worker parameters
          'import_json': True,
          'rows_to_skip': 0,
          'autodetect': True,
          'schema': None,
          'overwrite': True,
          'dont_create': False,
          # Resulting job config
          'job_config_source_format': 'NEWLINE_DELIMITED_JSON',
          'job_config_skip_leading_rows': None,
          'job_config_write_disposition': 'WRITE_TRUNCATE',
          'job_config_create_disposition': 'CREATE_IF_NEEDED'
      },
  )
  def test_load_table_from_uri_with_config(self,
                                           import_json,
                                           rows_to_skip,
                                           autodetect,
                                           schema,
                                           overwrite,
                                           dont_create,
                                           job_config_source_format,
                                           job_config_skip_leading_rows,
                                           job_config_write_disposition,
                                           job_config_create_disposition):
    worker_inst = storage_to_bq_importer.StorageToBQImporter(
        {
            'job_id': 'JOBID',
            'import_json': import_json,
            'rows_to_skip': rows_to_skip,
            'autodetect': autodetect,
            'schema': schema,
            'overwrite': overwrite,
            'dont_create': dont_create,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    mock_job = mock.create_autospec(
        bigquery.job.QueryJob, instance=True, spec_set=True)
    mock_job.error_result = None
    mock_job.state = 'DONE'
    mock_bq_client = mock.create_autospec(
        bigquery.Client, instance=True, spec_set=True)
    mock_bq_client.load_table_from_uri.return_value = mock_job
    self.enter_context(
        mock.patch.object(
            storage, 'Client', autospec=True, spec_set=True))
    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_client',
            return_value=mock_bq_client,
            autospec=True,
            spec_set=True))
    worker_inst._execute()
    mock_bq_client.load_table_from_uri.assert_called_once()
    load_table_call_args = mock_bq_client.load_table_from_uri.call_args
    call_job_config = load_table_call_args.kwargs['job_config']
    self.assertEqual(call_job_config.autodetect, autodetect)
    self.assertEqual(call_job_config.schema, schema)
    self.assertEqual(call_job_config.source_format,
                     job_config_source_format)
    self.assertEqual(call_job_config.skip_leading_rows,
                     job_config_skip_leading_rows)
    self.assertEqual(call_job_config.write_disposition,
                     job_config_write_disposition)
    self.assertEqual(call_job_config.create_disposition,
                     job_config_create_disposition)


if __name__ == '__main__':
  absltest.main()
