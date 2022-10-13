"""Tests for bq_script_executor."""

from unittest import mock

from absl.testing import absltest
from google.auth import credentials
from google.cloud import bigquery

from jobs.workers.bigquery import bq_script_executor


def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


class BQScriptExecutorTest(absltest.TestCase):

  def test_starts_query_job(self):
    worker_inst = bq_script_executor.BQScriptExecutor(
        {
            'job_id': 'JOBID',
            'script': 'CREATE OR REPLACE TABLE t AS SELECT * FROM mytable',
            'location': 'EU',
            'dry_run': False,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery jobs query response.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/query#response-body
    api_response = {
        'kind': 'bigquery#queryResponse',
        'schema': {
            'fields': [
                {
                    'name': 'model_name',
                    'type': 'STRING',
                    'mode': 'NULLABLE',
                },
                {
                    'name': 'score',
                    'type': 'FLOAT',
                    'mode': 'NULLABLE',
                }
            ]
        },
        'jobReference': {
            'projectId': 'PROJECT',
            'jobId': 'job_U6-11mAExu4QJquW3k2c_111yPIF',
            'location': 'EU',
        },
        'totalRows': '2',
        'rows': [
            {'f': [{'v': 'LTV v1'}, {'v': '20.70'}]},
            {'f': [{'v': 'LTV v1'}, {'v': '10.25'}]},
        ],
        'totalBytesProcessed': '1285317116',
        'jobComplete': True,
        'cacheHit': False,
    }

    bq_client = bigquery.Client(
        project='PROJECT', credentials=_make_credentials())
    self.enter_context(
        mock.patch.object(
            bq_client, '_call_api', autospec=True, return_value=api_response))
    self.enter_context(mock.patch.object(worker_inst, '_log', autospec=True))
    self.enter_context(
        mock.patch.object(
            worker_inst, '_get_client', autospec=True, return_value=bq_client))
    patched_wait = self.enter_context(
        mock.patch.object(worker_inst, '_wait', autospec=True))
    worker_inst.execute()
    patched_wait.assert_called_once()
    call_job: bigquery.QueryJob = patched_wait.call_args[0][0]
    self.assertIsInstance(call_job, bigquery.QueryJob)
    with self.subTest('Ensures query is passed with standard SQL config'):
      self.assertEqual(call_job.query,
                       'CREATE OR REPLACE TABLE t AS SELECT * FROM mytable')
      self.assertFalse(call_job.use_legacy_sql,
                       msg='We only support the standard SQL for this worker')
    with self.subTest('Storing results is delegated to the SQL query'):
      self.assertIsNone(call_job.create_disposition)
      self.assertIsNone(call_job.write_disposition)
      self.assertIsNone(call_job.destination)

  def test_dry_run_query(self):
    worker_inst = bq_script_executor.BQScriptExecutor(
        {
            'job_id': 'JOBID',
            'script': 'CREATE OR REPLACE TABLE t AS SELECT * FROM mytable',
            'location': 'EU',
            'dry_run': True,
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())

    # Stubs the BigQuery Job object.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/Job
    api_response = {
        'kind': 'bigquery#job',
        'statistics': {
            'totalBytesProcessed': '16013044',
            'query': {
                'totalBytesProcessed': '16013044',
                'totalBytesBilled': '0',
                'cacheHit': False,
                'totalBytesProcessedAccuracy': 'PRECISE',
                'mlStatistics': {
                    'modelType': 'LOGISTIC_REGRESSION',
                    'trainingType': 'HPARAM_TUNING'
                }
            }
        },
        'status': {'state': 'DONE'},
        'configuration': {
            'query': {
                'query': 'CREATE OR REPLACE TABLE t AS SELECT * FROM mytable',
                'priority': 'INTERACTIVE',
                'useQueryCache': False,
                'useLegacySql': False
            },
            'dryRun': True,
            'jobType': 'QUERY'
        }
    }
    bq_client = bigquery.Client(
        project='PROJECT', credentials=_make_credentials())
    bq_query_job_config = bigquery.QueryJobConfig(
        dry_run=True, use_query_cache=False)
    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_client',
            autospec=True,
            return_value=bq_client))
    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_dry_run_job_config',
            autospec=True,
            return_value=bq_query_job_config))
    self.enter_context(
        mock.patch.object(
            bq_client,
            '_call_api',
            autospec=True,
            return_value=api_response))
    patched_logger = self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    worker_inst.execute()
    self.assertSequenceEqual(
        [
            mock.call(mock.ANY),
            mock.call('This query will process 16.01 MB when run.'),
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )


if __name__ == '__main__':
  absltest.main()
