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
    shutil.copyfile(_datafile('dummy_stage_v3.py'),
                    pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v3.py'))

  def test_list_stages_in_default_directory(self):
    runner = testing.CliRunner()
    result = runner.invoke(stages.list_stages, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(result.output, 'dummy_stage_v3\n')

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
            return_value='dummy_stage_v3'))
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
            return_value='new_dummy_stage'))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_regions',
            autospec=True,
            return_value=('europe-west', 'europe-west1')))
    with self.subTest('Creates the stage file'):
      runner = testing.CliRunner()
      result = runner.invoke(stages.create, catch_exceptions=False)
      self.assertEqual(result.exit_code, 0, msg=result.output)
      self.assertRegex(result.output,
                       r'Stage file created\: .*new_dummy_stage.py$')
    with self.subTest('Validates content of the stage file'):
      stage_path = shared.get_default_stage_path()
      stage = shared.load_stage(stage_path)
      expected_context = shared.default_stage_context(
          shared.ProjectId('new_dummy_stage'))
      expected_context.spec_version = 'v3.0'
      self.assertEqual(stage.__dict__, expected_context.__dict__)

  def test_migrate_stage_from_v2_to_v3(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_regions',
            autospec=True,
            return_value=('us-central', 'us-central1')))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_stage_v2'))
    shutil.copyfile(_datafile('dummy_stage_v2.py'),
                    pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v2.py'))
    with self.subTest('Migrates the v2 stage to v3'):
      runner = testing.CliRunner()
      result = runner.invoke(stages.migrate, catch_exceptions=False)
      self.assertEqual(result.exit_code, 0, msg=result.output)
      self.assertRegex(result.output, r'Successfully migrated stage file at: ')
    with self.subTest('Validates content of the migrate stage file'):
      stage_path = shared.get_default_stage_path()
      stage = shared.load_stage(stage_path)
      self.assertEqual(stage.spec_version, 'v3.0')
      self.assertEqual(stage.project_id, 'crmint-dummy-v2')
      self.assertEqual(stage.project_region, 'europe-west')
      self.assertEqual(stage.workdir, '/tmp/crmint-dummy-v2')
      self.assertEqual(stage.database_project, 'crmint-dummy-v2')
      self.assertEqual(stage.database_region, 'europe-west1')
      self.assertEqual(stage.database_tier, 'db-g2-small')
      self.assertEqual(stage.database_name, 'old_name')
      self.assertEqual(stage.database_username, 'old_username')
      self.assertEqual(stage.database_password, 'old_password')
      self.assertEqual(stage.database_instance_name, 'old_instance_name')
      self.assertEqual(stage.notification_sender_email,
                       'noreply@crmint-dummy-v2.appspotmail.com')
      self.assertEqual(stage.gae_app_title, 'Crmint Dummy v2')

  def test_migrate_latest_spec_does_nothing(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_regions',
            autospec=True,
            return_value=('us-central', 'us-central1')))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_stage_v3'))
    shared.create_stage_file(
        pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v2.py'),
        shared.default_stage_context(shared.ProjectId('id')))
    stage_path = shared.get_default_stage_path()
    stage = shared.load_stage(stage_path)
    with self.subTest('Before migration spec version'):
      stage_path = shared.get_default_stage_path()
      stage = shared.load_stage(stage_path)
      self.assertEqual(stage.spec_version, constants.LATEST_STAGE_VERSION)
    with self.subTest('Migrate does nothing'):
      runner = testing.CliRunner()
      result = runner.invoke(stages.migrate, catch_exceptions=False)
      self.assertEqual(result.exit_code, 0, msg=result.output)
      self.assertRegex(result.output, r'Already latest version detected: ')
    with self.subTest('After migration spec version'):
      stage_path = shared.get_default_stage_path()
      stage = shared.load_stage(stage_path)
      self.assertEqual(stage.spec_version, constants.LATEST_STAGE_VERSION)


if __name__ == '__main__':
  absltest.main()
