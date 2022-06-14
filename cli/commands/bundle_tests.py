"""Tests for cli.commands.stages."""

import os
import pathlib
import shutil
import subprocess
from unittest import mock

from absl.testing import absltest
from click import testing

from cli.commands import bundle
from cli.utils import constants
from cli.utils import shared

DATA_DIR = os.path.join(os.path.dirname(__file__), '../testdata')


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


class BundleTest(absltest.TestCase):

  def setUp(self):
    super().setUp()

    def _system_call(cmd, **unused_kwargs):
      mock_result = mock.create_autospec(
          subprocess.CompletedProcess, instance=True)
      mock_result.returncode = 0
      mock_result.stdout = b'output'
      mock_result.stderr = b''
      if 'billingAccountName' in cmd:
        mock_result.stdout = b'billingAccountName/XXX-YYY'
      elif 'billingEnabled' in cmd:
        mock_result.stdout = b'True'
      return mock_result

    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=_system_call))
    # Overrides the default stage directory with a custom temporary directory.
    tmp_stage_dir = self.create_tempdir('stage_dir')
    self.enter_context(
        mock.patch.object(constants, 'STAGE_DIR', tmp_stage_dir.full_path))
    shutil.copyfile(_datafile('dummy_stage_v2.py'),
                    pathlib.Path(constants.STAGE_DIR, 'old_dummy_stage.py'))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='old_dummy_stage'))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_regions',
            autospec=True,
            return_value=('us-central', 'us-central1')))

  def test_can_run_install(self):
    runner = testing.CliRunner()
    result = runner.invoke(bundle.install, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertIn('>>>> Create stage', result.output)
    self.assertIn('>>>> Migrate stage', result.output)
    self.assertIn('Successfully migrated stage file', result.output)
    self.assertIn('>>>> Setup', result.output)
    self.assertIn('>>>> Deploy', result.output)

if __name__ == '__main__':
  absltest.main()
