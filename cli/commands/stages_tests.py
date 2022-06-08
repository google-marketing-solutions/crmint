"""Tests for cli.commands.stages."""

import os
import pathlib
import shutil
import subprocess
import textwrap
from unittest import mock

from absl.testing import absltest
import click
from click import testing

from cli.commands import stages
from cli.utils import constants
from cli.utils import shared

DATA_DIR = os.path.join(os.path.dirname(__file__), '../testdata')


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


class GetRegionTests(absltest.TestCase):

  def test_get_regions_with_existing_app_engine(self):
    mock_result = mock.create_autospec(subprocess.CompletedProcess,
                                       instance=True)
    mock_result.returncode = 0
    mock_result.stdout = b'locationId: europe-west'
    mock_result.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_result))
    self.assertEqual(stages._get_regions(shared.ProjectId('dummy_stage_v3')),
                     ('europe-west', 'europe-west1'))

  def test_get_regions_no_app_engine(self):
    # No appengine
    mock_result_1 = mock.create_autospec(subprocess.CompletedProcess,
                                         instance=True)
    mock_result_1.returncode = 1
    mock_result_1.stdout = b'output'
    mock_result_1.stderr = b'error'
    # List of regions
    list_of_regions_bytes = textwrap.dedent("""\
        asia-east1
        asia-northeast1
        asia-southeast1
        australia-southeast1
        europe-west
        europe-west2
        europe-west3
        us-central
        us-east1
        us-east4
        us-west1
        us-west2
        us-west3
        us-west4""").encode('utf-8')
    mock_result_2 = mock.create_autospec(subprocess.CompletedProcess,
                                         instance=True)
    mock_result_2.returncode = 0
    mock_result_2.stdout = list_of_regions_bytes
    mock_result_2.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess,
            'run',
            autospec=True,
            side_effect=[mock_result_1, mock_result_2]))
    self.enter_context(
        mock.patch.object(click, 'prompt', autospec=True, return_value=4))
    self.assertEqual(stages._get_regions(shared.ProjectId('dummy_stage_v3')),
                     ('australia-southeast1', 'australia-southeast1'))


class StagesTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    mock_result = mock.create_autospec(subprocess.CompletedProcess,
                                       instance=True)
    mock_result.returncode = 0
    mock_result.stdout = b'output'
    mock_result.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_result))
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

  def test_create_new_stage_file(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='new_dummy_stage'))
    self.enter_context(
        mock.patch.object(
            stages,
            '_get_regions',
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
      expected_context = stages._default_stage_context(
          shared.ProjectId('new_dummy_stage'))
      expected_context.spec_version = 'v3.0'
      self.assertEqual(stage.__dict__, expected_context.__dict__)

  def test_migrate_stage_from_v2_to_v3(self):
    self.enter_context(
        mock.patch.object(
            stages,
            '_get_regions',
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
            stages,
            '_get_regions',
            autospec=True,
            return_value=('us-central', 'us-central1')))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_stage_v3'))
    stages._create_stage_file(
        pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v2.py'),
        stages._default_stage_context(shared.ProjectId('id')))
    stage_path = shared.get_default_stage_path()
    stage = shared.load_stage(stage_path)
    with self.subTest('Before migration spec version'):
      stage_path = shared.get_default_stage_path()
      stage = shared.load_stage(stage_path)
      self.assertEqual(stage.spec_version, stages.LATEST_STAGE_VERSION)
    with self.subTest('Migrate does nothing'):
      runner = testing.CliRunner()
      result = runner.invoke(stages.migrate, catch_exceptions=False)
      self.assertEqual(result.exit_code, 0, msg=result.output)
      self.assertRegex(result.output, r'Already latest version detected: ')
    with self.subTest('After migration spec version'):
      stage_path = shared.get_default_stage_path()
      stage = shared.load_stage(stage_path)
      self.assertEqual(stage.spec_version, stages.LATEST_STAGE_VERSION)


if __name__ == '__main__':
  absltest.main()
