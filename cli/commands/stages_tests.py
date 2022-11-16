"""Tests for cli.commands.stages."""

import os
import pathlib
import shutil
import subprocess
from unittest import mock

from absl.testing import absltest
from click import testing

from cli.commands import stages
from cli.utils import constants
from cli.utils import shared
from cli.utils import test_helpers

DATA_DIR = os.path.join(os.path.dirname(__file__), '../testdata')


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


class StagesTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    side_effect_run = test_helpers.mock_subprocess_result_side_effect(
        stdout=b'output', stderr=b'')
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
    shutil.copyfile(
        _datafile('dummy_project_with_vpc.tfvars'),
        pathlib.Path(constants.STAGE_DIR, 'dummy_project_with_vpc.tfvars'))

  def test_list_stages_in_default_directory(self):
    runner = testing.CliRunner()
    result = runner.invoke(stages.list_stages, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(result.output, 'dummy_project_with_vpc\n')

  def test_list_stages_in_custom_directory(self):
    runner = testing.CliRunner()
    empty_stage_dir = self.create_tempdir('empty_stage_dir')
    result = runner.invoke(
        stages.list_stages,
        args=[f'--stage_dir={empty_stage_dir}'],
        catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(result.output, '')

  def test_create_new_stage_file_already_exists(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_project_with_vpc'))
    runner = testing.CliRunner()
    result = runner.invoke(stages.create, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertIn('already exists', result.output)

  def test_create_new_stage_file(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='new_dummy_project'))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_user_email',
            autospec=True,
            return_value='user@example.com'))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_region',
            autospec=True,
            return_value='europe-west1'))
    runner = testing.CliRunner()
    result = runner.invoke(stages.create, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(result.output,
                     r'Stage file created\: .*new_dummy_project.tfvars$')

  def test_migrate_shows_deprecation(self):
    runner = testing.CliRunner()
    result = runner.invoke(stages.migrate, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(result.output, r'Deprecated')


if __name__ == '__main__':
  absltest.main()
