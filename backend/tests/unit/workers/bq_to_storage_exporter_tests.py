"""Tests for bq_to_storage_exporter."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials
from google.cloud import bigquery

from jobs.workers.bigquery import bq_to_storage_exporter


def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


class BQToStorageExporterTest(parameterized.TestCase):

  @parameterized.parameters(
      {'export_json': False, 'destination_format': 'CSV',
       'print_header': True,
       'export_gzip': False, 'compression': 'NONE'},
      {'export_json': False, 'destination_format': 'CSV',
       'print_header': False,
       'export_gzip': True, 'compression': 'GZIP'},
      {'export_json': True, 'destination_format': 'NEWLINE_DELIMITED_JSON',
       'print_header': True,
       'export_gzip': True, 'compression': 'GZIP'},
  )
  def test_extract_table_with_config(self,
                                     export_json,
                                     destination_format,
                                     print_header,
                                     export_gzip,
                                     compression):
    worker_inst = bq_to_storage_exporter.BQToStorageExporter(
        {
            'job_id': 'JOBID',
            'export_json': export_json,
            'print_header': print_header,
            'export_gzip': export_gzip,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    mock_job = mock.create_autospec(
        bigquery.job.QueryJob, instance=True, spec_set=True)
    mock_job.error_result = None
    mock_job.state = 'DONE'
    mock_client = mock.create_autospec(
        bigquery.Client, instance=True, spec_set=True)
    mock_client.extract_table.return_value = mock_job
    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_client',
            return_value=mock_client,
            autospec=True,
            spec_set=True))
    worker_inst._execute()
    mock_client.extract_table.assert_called_once()
    call_job_config = mock_client.extract_table.call_args.kwargs['job_config']
    self.assertEqual(call_job_config.print_header, print_header)
    self.assertEqual(call_job_config.destination_format, destination_format)
    self.assertEqual(call_job_config.compression, compression)


if __name__ == '__main__':
  absltest.main()
