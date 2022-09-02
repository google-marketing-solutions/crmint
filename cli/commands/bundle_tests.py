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
from cli.utils import test_helpers

DATA_DIR = os.path.join(os.path.dirname(__file__), '../testdata')


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


class BundleTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    side_effect_run = test_helpers.mock_subprocess_result_side_effect()
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=side_effect_run))
    # `create_tempfile` needs access to --test_tmpdir, however in the OSS world
    # pytest doesn't run `absltest.main`, so we need to init flags ourselves.
    test_helpers.initialize_flags_with_defaults()
    # Overrides the default stage directory with a custom temporary directory.
    tmp_stage_dir = self.create_tempdir('stage_dir')
    self.enter_context(
        mock.patch.object(constants, 'STAGE_DIR', tmp_stage_dir.full_path))
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

  def test_can_run_install_without_stage_file(self):
    runner = testing.CliRunner()
    result = runner.invoke(bundle.install, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertIn('>>>> Create stage', result.output)
    self.assertIn('>>>> Migrate stage', result.output)
    self.assertIn('>>>> Checklist', result.output)
    self.assertIn('>>>> Setup', result.output)
    self.assertIn('>>>> Deploy', result.output)

  def test_stage_file_has_use_vpc_enabled(self):
    runner = testing.CliRunner()
    result = runner.invoke(
        bundle.install, args=['--use_vpc'], catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    stage = shared.load_stage(
        pathlib.Path(constants.STAGE_DIR, 'old_dummy_stage.py'))
    self.assertTrue(stage.use_vpc)

  def test_can_run_install_with_stage_migration(self):
    shutil.copyfile(_datafile('dummy_stage_v2.py'),
                    pathlib.Path(constants.STAGE_DIR, 'old_dummy_stage.py'))
    runner = testing.CliRunner()
    result = runner.invoke(bundle.install, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertIn('>>>> Create stage', result.output)
    self.assertIn('>>>> Migrate stage', result.output)
    self.assertIn('Successfully migrated stage file', result.output)
    self.assertIn('>>>> Checklist', result.output)
    self.assertIn('>>>> Setup', result.output)
    self.assertIn('>>>> Deploy', result.output)

  def test_can_run_install_latest_stage_version(self):
    shutil.copyfile(_datafile('dummy_stage_v3.py'),
                    pathlib.Path(constants.STAGE_DIR, 'old_dummy_stage.py'))
    runner = testing.CliRunner()
    result = runner.invoke(bundle.install, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertIn('>>>> Create stage', result.output)
    self.assertIn('>>>> Migrate stage', result.output)
    self.assertIn('Already latest version detected', result.output)
    self.assertIn('>>>> Checklist', result.output)
    self.assertIn('>>>> Setup', result.output)
    self.assertIn('>>>> Deploy', result.output)

if __name__ == '__main__':
  absltest.main()
