"""Tests for vertexai_batch_predictor_to_bq."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials

from google.cloud import aiplatform

from google.cloud.aiplatform import models
from google.cloud.aiplatform_v1.types import (
    batch_prediction_job as gca_batch_prediction_job,
    job_state as gca_job_state,
)

from jobs.workers.vertexai import vertexai_batch_predictor_to_bq

_TEST_PROJECT = 'test-project'

_TEST_DATASET_DISPLAY_NAME = 'my_dataset_1234'
_TEST_DATASET_TABLE_NAME = 'my_table_1234'

_TEST_VERETXAI_PREDICTION_JOB_NAME = 'test-batch-prediction-job-name'

def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


class VertexAIBatchPredictorToBQTest(parameterized.TestCase):

  @parameterized.parameters(
      {
          'cfg_clean_up': False,
          'cfg_vertexai_batch_prediction_name':
              _TEST_VERETXAI_PREDICTION_JOB_NAME,
      },
      {
          'cfg_clean_up': True,
          'cfg_vertexai_batch_prediction_name':
              _TEST_VERETXAI_PREDICTION_JOB_NAME
      }
  )
  def test_vertexai_batch_predictor_to_bq(self, cfg_clean_up,
                                          cfg_vertexai_batch_prediction_name):

    worker_inst = vertexai_batch_predictor_to_bq.VertexAIBatchPredictorToBQ(
        # params
        {
            'clean_up':
                cfg_clean_up,
            'vertexai_batch_prediction_name':
                cfg_vertexai_batch_prediction_name,
            'project_id':
                _TEST_PROJECT,
            'dataset_id':
                _TEST_DATASET_DISPLAY_NAME,
            'table_id':
                _TEST_DATASET_TABLE_NAME
        },
        # pipeline_id: int,
        pipeline_id=1,
        # job_id: int,
        job_id=1,
        # logger_project: Optional[str] = None,
        logger_project=_TEST_PROJECT,
        # logger_credentials: Optional[credentials.Credentials] = None
        logger_credentials=_make_credentials()
    )

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_project_id',
            return_value=_TEST_PROJECT,
            autospec=True,
            spec_set=True))

    # mock ModelServiceClient and then inject as result of
    # _get_vertexai_model_client
    mock_model_client = mock.create_autospec(
        aiplatform.gapic.ModelServiceClient, instance=True, spec_set=True)

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_vertexai_model_client',
            return_value=mock_model_client,
            autospec=True,
            spec_set=True))
    # mock Batch Prediction Job
    mock_batch_prediction_job = mock.Mock(
        spec=gca_batch_prediction_job.BatchPredictionJob
    )
    mock_batch_prediction_job.state = gca_job_state.JobState.JOB_STATE_SUCCEEDED
    mock_batch_prediction_job.name = _TEST_VERETXAI_PREDICTION_JOB_NAME
    mock_batch_prediction_job.resource_name = _TEST_VERETXAI_PREDICTION_JOB_NAME

    # mock DatasetServiceClient and then inject as result of
    # _get_vertexai_dataset_client
    mock_job_client = mock.create_autospec(
        aiplatform.gapic.JobServiceClient, instance=True, spec_set=True)

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_vertexai_job_client',
            return_value=mock_job_client,
            autospec=True,
            spec_set=True))

    # mock model
    mock_model = mock.Mock(models.Model)
    mock_model.batch_predict.return_result = mock_batch_prediction_job

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_model',
            return_value=mock_model,
            autospec=True,
            spec_set=True))

    # mock logger
    self.enter_context(
        mock.patch.object(
            worker_inst, 'log_info',
            return_value=None,
            autospec=True,
            spec_set=True))

    # mock wait
    # mock logger
    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_wait_for_job',
            return_value=None,
            autospec=True,
            spec_set=True))

    worker_inst._execute()
    if cfg_clean_up:
      self.enter_context(
          mock.patch.object(
              worker_inst,
              '_clean_up_batch_predictions',
              return_value=None,
              autospec=True,
              spec_set=True))

    mock_model.batch_predict.assert_called_once()


if __name__ == '__main__':
  absltest.main()
