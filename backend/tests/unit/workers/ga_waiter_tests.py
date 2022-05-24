"""Tests for ga_waiter."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.auth import credentials

from jobs.workers.ga import ga_utils
from jobs.workers.ga import ga_waiter


def _make_credentials():
  return mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)


class GADataImportUploadWaiterTest(parameterized.TestCase):

  @parameterized.parameters(
      (ga_utils.UploadStatus.PENDING, True),
      (ga_utils.UploadStatus.COMPLETED, False),
  )
  def test_respawn_on_status_pending(self, upload_status, respawned):
    worker_inst = ga_waiter.GADataImportUploadWaiter(
        {'job_id': 'JOBID'},
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    self.enter_context(
        mock.patch.object(ga_utils, 'get_client', autospec=True, spec_set=True))
    self.enter_context(
        mock.patch.object(
            ga_utils,
            'get_dataimport_upload_status',
            return_value=upload_status,
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
    if respawned:
      patched_enqueue.assert_called_once_with(
          'GADataImportUploadWaiter', mock.ANY, mock.ANY)
    else:
      patched_enqueue.assert_not_called()


if __name__ == '__main__':
  absltest.main()
