"""Tests for bq_to_vertexai_dataset."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials
from google.cloud import aiplatform
from google.cloud.aiplatform import datasets as gca_datasets
from jobs.workers.bigquery import bq_to_vertexai_dataset

_TEST_PROJECT = 'test-project'

# dataset
_TEST_DISPLAY_NAME = 'my_dataset_1234'
_TEST_TABLE_NAME = 'my_table_1234'


def _make_credentials():
  creds = mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)
  return creds


class BQToVertexAIDatasetTest(parameterized.TestCase):

  @parameterized.parameters(
      {
          'cfg_vertexai_dataset_name': _TEST_DISPLAY_NAME,
          'cfg_clean_up': True
      },
      {
          'cfg_vertexai_dataset_name': _TEST_DISPLAY_NAME,
          'cfg_clean_up': False
      },
      {
          'cfg_vertexai_dataset_name': None,
          'cfg_clean_up': True
      },
  )
  def test_create_vertexai_dataset(self, cfg_vertexai_dataset_name,
                                   cfg_clean_up):

    if not cfg_vertexai_dataset_name:
      display_name = f'{_TEST_PROJECT}.{_TEST_DISPLAY_NAME}.{_TEST_TABLE_NAME}'
    else:
      display_name = cfg_vertexai_dataset_name

    bq_source_uri = f'bq://{_TEST_PROJECT}.{_TEST_DISPLAY_NAME}.{_TEST_TABLE_NAME}'

    worker_inst = bq_to_vertexai_dataset.BQToVertexAIDataset(
        # params
        {
            'vertexai_dataset_name': cfg_vertexai_dataset_name,
            'clean_up': cfg_clean_up,
            'bq_project_id': _TEST_PROJECT,
            'bq_dataset_id': _TEST_DISPLAY_NAME,
            'bq_table_id': _TEST_TABLE_NAME
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

    mock_datasets_client = mock.Mock(spec=aiplatform.gapic.DatasetServiceClient)

    mock_tabular_dataset_client = mock.create_autospec(
        aiplatform.TabularDataset, instance=True, spec_set=True)
    mock_tabular_dataset = mock.create_autospec(
        gca_datasets.TabularDataset, instance=True, spec_set=True)
    mock_tabular_dataset.wait.return_value = None
    mock_tabular_dataset_client.create.return_value = mock_tabular_dataset

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
            '_get_vertexai_dataset_client',
            return_value=mock_datasets_client,
            autospec=True,
            spec_set=True))

    self.enter_context(
        mock.patch.object(
            worker_inst,
            '_get_tabular_dataset_client',
            return_value=mock_tabular_dataset_client,
            autospec=True,
            spec_set=True))

    self.enter_context(
        mock.patch.object(
            worker_inst,
            'log_info',
            return_value='logger',
            autospec=True,
            spec_set=True))

    if cfg_clean_up:
      self.enter_context(
          mock.patch.object(
              worker_inst,
              '_clean_up_datasets',
              return_value=None,
              autospec=True,
              spec_set=True))

    worker_inst._execute()

    # asserts
    if not cfg_vertexai_dataset_name:
      # when dataset_name is not provided then dataset name
      # should be set to default name
      mock_tabular_dataset_client.create.assert_called_once_with(
          display_name=display_name, bq_source=bq_source_uri)
    else:
      mock_tabular_dataset_client.create.assert_called()

if __name__ == '__main__':
  absltest.main()
