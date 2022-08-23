"""Tests for ga_waiter."""

from unittest import mock
from unittest.mock import patch

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials
from google.cloud import aiplatform
from google.cloud.aiplatform_v1.types import (
    pipeline_state as gca_pipeline_state,
    training_pipeline as gca_training_pipeline,
    batch_prediction_job as gca_batch_prediction_job,
    job_state as gca_job_state,
)

from jobs.workers import worker
from jobs.workers.vertexai import vertexai_waiter

_TEST_PROJECT = "test-project"
_TEST_LOCATION = "us-central1"

_TEST_VERETXAI_PREDICTION_JOB_ID = "abcdef123456"

_TEST_PIPELINE_RESOURCE_NAME = (
    "projects/my-project/locations/us-central1/trainingPipelines/12345"
)

_TEST_BATCH_PREDICTION_JOB_NAME = "batchjob-123456"


def _make_credentials():
  return mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)


class VertexAIWaiterTests(parameterized.TestCase):

  @parameterized.parameters(
      {"cfg_worker_class": "VertexAIBatchPredictorToBQ"},
      {"cfg_worker_class": "VertexAITabularTrainer"},
  )
  def test_execute(self, cfg_worker_class):
    worker_inst = vertexai_waiter.VertexAIWaiter(
        # params
        {
            "worker_class": cfg_worker_class,
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

    if cfg_worker_class == "VertexAIBatchPredictorToBQ":
      with patch.object(
          worker_inst, "_execute_batch_predictor",
          return_value=None) as mock_method:
        worker_inst._execute()
        mock_method.assert_called_once()
    elif cfg_worker_class == "VertexAITabularTrainer":
      with patch.object(
          worker_inst, "_execute_tabular_trainer",
          return_value=None) as mock_method:
        worker_inst._execute()
        mock_method.assert_called_once()

  @parameterized.parameters(
      {
          "cfg_pipeline_state":
              gca_pipeline_state.PipelineState.PIPELINE_STATE_SUCCEEDED
      },
      {
          "cfg_pipeline_state":
              gca_pipeline_state.PipelineState.PIPELINE_STATE_FAILED
      },
      {
          "cfg_pipeline_state":
              gca_pipeline_state.PipelineState.PIPELINE_STATE_RUNNING
      },
  )
  def test_execute_tabular_trainer(self, cfg_pipeline_state):
    worker_inst = vertexai_waiter.VertexAIWaiter(
        # params
        {
            "id": _TEST_VERETXAI_PREDICTION_JOB_ID,
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

    # Mock _get_location_from_pipeline_name
    self.enter_context(
        mock.patch.object(
            worker_inst,
            "_get_location_from_pipeline_name",
            return_value=_TEST_LOCATION,
            autospec=True,
            spec_set=True))

    # mock PipelineServiceClient and then inject as
    # result of _get_vertexai_pipeline_client
    mock_pipeline_client = mock.create_autospec(
        aiplatform.gapic.PipelineServiceClient, instance=True, spec_set=True)

    mock_pipeline_client.get_training_pipeline.return_value = (
        gca_training_pipeline.TrainingPipeline(
            name=_TEST_PIPELINE_RESOURCE_NAME, state=cfg_pipeline_state))

    self.enter_context(
        mock.patch.object(
            worker_inst,
            "_get_vertexai_pipeline_client",
            return_value=mock_pipeline_client,
            autospec=True,
            spec_set=True))

    self.enter_context(mock.patch.object(worker_inst, "_log", autospec=True))

    if cfg_pipeline_state == gca_pipeline_state.PipelineState.PIPELINE_STATE_SUCCEEDED:
      with patch.object(worker_inst, "log_info", return_value=None) as mock_log:
        worker_inst._execute_tabular_trainer()
        mock_log.assert_called_once_with("Finished successfully!")
    elif cfg_pipeline_state == gca_pipeline_state.PipelineState.PIPELINE_STATE_FAILED:
      with self.assertRaises(worker.WorkerException):
        worker_inst._execute_tabular_trainer()
    elif cfg_pipeline_state == gca_pipeline_state.PipelineState.PIPELINE_STATE_RUNNING:
      patched_enqueue = self.enter_context(
          mock.patch.object(
              worker_inst, "_enqueue", autospec=True, spec_set=True))
      worker_inst._execute_tabular_trainer()
      patched_enqueue.assert_called_once()

  @parameterized.parameters(
      {"cfg_job_state": gca_job_state.JobState.JOB_STATE_FAILED},
      {"cfg_job_state": gca_job_state.JobState.JOB_STATE_FAILED},
      {"cfg_job_state": gca_job_state.JobState.JOB_STATE_RUNNING},
  )
  def test_execute_batch_predictor(self, cfg_job_state):
    worker_inst = vertexai_waiter.VertexAIWaiter(
        # params
        {
            "id": _TEST_BATCH_PREDICTION_JOB_NAME,
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

    # Mock _get_location_from_pipeline_name
    self.enter_context(
        mock.patch.object(
            worker_inst,
            "_get_location_from_job_name",
            return_value=_TEST_LOCATION,
            autospec=True,
            spec_set=True))

    # mock JobServiceClient and then inject as
    # result of _get_vertexai_pipeline_client
    mock_job_client = mock.create_autospec(
        aiplatform.gapic.JobServiceClient, instance=True, spec_set=True)

    mock_job_client.get_batch_prediction_job.return_value = (
        gca_batch_prediction_job.BatchPredictionJob(
            name=_TEST_BATCH_PREDICTION_JOB_NAME,
            display_name=_TEST_BATCH_PREDICTION_JOB_NAME,
            state=cfg_job_state,
        ))

    self.enter_context(
        mock.patch.object(
            worker_inst,
            "_get_vertexai_job_client",
            return_value=mock_job_client,
            autospec=True,
            spec_set=True))

    self.enter_context(mock.patch.object(worker_inst, "_log", autospec=True))

    if cfg_job_state == gca_job_state.JobState.JOB_STATE_SUCCEEDED:
      with patch.object(worker_inst, "log_info", return_value=None) as mock_log:
        worker_inst._execute_batch_predictor()
        mock_log.assert_called_once_with("Finished successfully!")
    elif cfg_job_state == gca_job_state.JobState.JOB_STATE_FAILED:
      with self.assertRaises(worker.WorkerException):
        worker_inst._execute_batch_predictor()
    elif cfg_job_state == gca_job_state.JobState.JOB_STATE_RUNNING:
      patched_enqueue = self.enter_context(
          mock.patch.object(
              worker_inst, "_enqueue", autospec=True, spec_set=True))
      worker_inst._execute_batch_predictor()
      patched_enqueue.assert_called_once()


if __name__ == "__main__":
  absltest.main()
