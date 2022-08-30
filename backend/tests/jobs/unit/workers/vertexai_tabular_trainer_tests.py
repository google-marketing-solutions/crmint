"""Tests for vertexai_tabular_trainer.py"""
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials
from google.cloud import aiplatform
from google.cloud.aiplatform import schema
from google.cloud.aiplatform_v1.types import (
    dataset as gca_dataset,
    model as gca_model,
    pipeline_state as gca_pipeline_state,
    training_pipeline as gca_training_pipeline,
)
from jobs.workers.vertexai import vertexai_tabular_trainer


_TEST_PROJECT = 'test-project'

_TEST_DATASET_DISPLAY_NAME = 'my_dataset_1234'
_TEST_DATASET_METADATA_SCHEMA_URI_TABULAR = schema.dataset.metadata.tabular

_TEST_AUTOML_JOB_RESOURCE_NAME = 'test-automl-job'
_TEST_VERETXAI_MODEL_NAME = 'test-model'
_TEST_BUDGET_HOURS = 1
_TEST_PIPELINE_RESOURCE_NAME = (
    'projects/my-project/locations/us-central1/trainingPipelines/12345'
)


def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


class VertexAITabularTrainerTest(parameterized.TestCase):

  @parameterized.parameters(
      {
          'cfg_vertexai_model_name': 'xxxx',
          'cfg_clean_up': True,
          'cfg_budget_hours': _TEST_BUDGET_HOURS,
          'cfg_target_column': 'converters',
      }
  )
  def test_execute(self, cfg_vertexai_model_name, cfg_clean_up,
                   cfg_budget_hours, cfg_target_column):
    worker_inst = vertexai_tabular_trainer.VertexAITabularTrainer(
        # params
        {
            'clean_up': cfg_clean_up,
            'vertexai_model_name': cfg_vertexai_model_name,
            'budget_hours': cfg_budget_hours,
            'target_column': cfg_target_column
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

    mock_dataset = mock.Mock(gca_dataset.Dataset(
        display_name=_TEST_DATASET_DISPLAY_NAME,
        metadata_schema_uri=_TEST_DATASET_METADATA_SCHEMA_URI_TABULAR,
    ))

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_project_id',
            return_value=_TEST_PROJECT,
            autospec=True,
            spec_set=True))

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_vertexai_tabular_dataset',
            return_value=mock_dataset,
            autospec=True,
            spec_set=True))
    # mock DatasetServiceClient and then inject as result of
    # _get_vertexai_dataset_client
    mock_dataset_client = mock.create_autospec(
        aiplatform.gapic.DatasetServiceClient,
        instance=True,
        spec_set=True)

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_vertexai_dataset_client',
            return_value=mock_dataset_client,
            autospec=True,
            spec_set=True))

    # mock PipelineServiceClient and then inject as result of
    # _get_vertexai_pipeline_client
    mock_pipeline_client = mock.create_autospec(
        aiplatform.gapic.PipelineServiceClient,
        instance=True,
        spec_set=True)

    mock_training_pipeline = mock.Mock(
        gca_training_pipeline.TrainingPipeline(
            name=_TEST_PIPELINE_RESOURCE_NAME,
            state=gca_pipeline_state.PipelineState.PIPELINE_STATE_SUCCEEDED,
            model_to_upload=gca_model.Model(name=_TEST_VERETXAI_MODEL_NAME),
        ))

    mock_pipeline_client.get_training_pipeline.return_value = mock_training_pipeline

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_vertexai_pipeline_client',
            return_value=mock_pipeline_client,
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

    # mock AutoMLTabularTrainingJob and then inject as result of
    # _create_automl_tabular_training_job
    mock_automl_job = mock.create_autospec(
        aiplatform.AutoMLTabularTrainingJob, instance=True, spec_set=True)

    mock_automl_job.run.return_value = None
    mock_automl_job.wait_for_resource_creation.return_value = None
    mock_automl_job.resource_name = _TEST_AUTOML_JOB_RESOURCE_NAME

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_create_automl_tabular_training_job',
            return_value=mock_automl_job,
            autospec=True,
            spec_set=True))

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_wait_for_pipeline',
            return_value=None,
            autospec=True,
            spec_set=True))

    worker_inst._execute()
    mock_automl_job.run.assert_called_once_with(
        dataset=mock_dataset,
        target_column=cfg_target_column,
        budget_milli_node_hours=cfg_budget_hours * 1000,
        model_display_name=cfg_vertexai_model_name,
        is_default_version=True,
        disable_early_stopping=False,
        sync=False
    )

if __name__ == '__main__':
  absltest.main()
