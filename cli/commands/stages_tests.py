"""Tests for cli.commands.stages."""

import os
import pathlib
import shutil
import subprocess
import textwrap
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
        _datafile('dummy_project_with_vpc.tfvars.json'),
        pathlib.Path(constants.STAGE_DIR, 'dummy_project_with_vpc.tfvars.json'))

  def test_list_stages_in_default_directory(self):
    shutil.copyfile(
        _datafile('dummy_project_with_vpc.tfvars.json'),
        pathlib.Path(constants.STAGE_DIR, 'other-environment.tfvars.json'))
    runner = testing.CliRunner()
    result = runner.invoke(stages.list_stages, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(result.output,
                     'dummy_project_with_vpc\nother-environment\n')

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
                     r'Stage file created\: .*new_dummy_project.tfvars.json$')

  def test_migrate_shows_deprecation(self):
    runner = testing.CliRunner()
    result = runner.invoke(stages.migrate, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(result.output, r'Deprecated')

  def test_can_update_stage_file_to_new_version(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_project_with_vpc'))
    self.enter_context(
        mock.patch.object(
            shared,
            'list_available_tags',
            autospec=True,
            return_value=['3.2', '3.1', '3.0']))
    runner = testing.CliRunner()
    result = runner.invoke(
        stages.update,
        args=['--version=3.2'],
        catch_exceptions=False)
    with self.subTest('Validates command line output'):
      self.assertEqual(0, result.exit_code, msg=result.output)
      self.assertIn('Stage updated to version: 3.2', result.output)
    with self.subTest('Validates content of new stage file'):
      updated_stage = shared.load_stage(
          pathlib.Path(constants.STAGE_DIR,
                       'dummy_project_with_vpc.tfvars.json'))
      self.assertEqual(
          updated_stage.frontend_image.split(':')[1], '3.2')
      self.assertEqual(
          updated_stage.controller_image.split(':')[1], '3.2')
      self.assertEqual(
          updated_stage.jobs_image.split(':')[1], '3.2')

  def test_update_to_latest_version_if_none_specified(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_project_with_vpc'))
    self.enter_context(
        mock.patch.object(
            shared,
            'list_available_tags',
            autospec=True,
            return_value=['3.3', '3.2', '3.1', '3.0']))
    runner = testing.CliRunner()
    result = runner.invoke(stages.update, catch_exceptions=False)
    with self.subTest('Validates command line output'):
      self.assertEqual(0, result.exit_code, msg=result.output)
      self.assertIn('Stage updated to version: 3.3', result.output)
    with self.subTest('Validates content of new stage file'):
      updated_stage = shared.load_stage(
          pathlib.Path(constants.STAGE_DIR,
                       'dummy_project_with_vpc.tfvars.json'))
      self.assertEqual(
          updated_stage.frontend_image.split(':')[1], '3.3')
      self.assertEqual(
          updated_stage.controller_image.split(':')[1], '3.3')
      self.assertEqual(
          updated_stage.jobs_image.split(':')[1], '3.3')

  def test_suggest_fix_if_version_not_available(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_project_with_vpc'))
    self.enter_context(
        mock.patch.object(
            shared,
            'list_available_tags',
            autospec=True,
            return_value=['3.2', '3.1', '3.0']))
    runner = testing.CliRunner()
    result = runner.invoke(
        stages.update,
        args=['--version=4.0'],
        catch_exceptions=False)
    with self.subTest('Validates command line output'):
      self.assertEqual(1, result.exit_code, msg=result.output)
      self.assertIn('Pick a version from: ', result.output)

  def test_can_allow_new_user_in_iap_settings(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_project_with_vpc'))
    runner = testing.CliRunner()
    result = runner.invoke(
        stages.allow_users,
        args=['me@example.com,you@example.com'],
        catch_exceptions=False)
    with self.subTest('Validates command line output'):
      self.assertEqual(0, result.exit_code, msg=result.output)
      self.assertIn('Stage updated with new IAP users', result.output)
    with self.subTest('Validates content of new stage file'):
      updated_stage = shared.load_stage(
          pathlib.Path(constants.STAGE_DIR,
                       'dummy_project_with_vpc.tfvars.json'))
      self.assertIn('user:me@example.com', updated_stage.iap_allowed_users)
      self.assertIn('user:you@example.com', updated_stage.iap_allowed_users)

  def test_validates_stdout_on_create_stage_with_project_id(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='other_gcp_project'))
    self.enter_context(
        mock.patch.object(
            shared,
            'list_user_project_ids',
            autospec=True,
            return_value=['other_gcp_project', 'my_gcp_project']))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_region',
            autospec=True,
            return_value='europe-west1'))
    runner = testing.CliRunner()
    result = runner.invoke(stages.create, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(
        result.output,
        textwrap.dedent("""\
            >>>> Create stage
                 Project ID found: other_gcp_project
            ---> Detect env variables
            ---> Activate Cloud services ✓
            ---> Retrieve gcloud current user ✓
            Stage file created: .*/other_gcp_project.tfvars.json
            """))

  def test_validates_stdout_on_create_stage_without_project_id(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value=''))
    self.enter_context(
        mock.patch.object(
            shared,
            'list_user_project_ids',
            autospec=True,
            return_value=['other_gcp_project', 'my_gcp_project']))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_region',
            autospec=True,
            return_value='europe-west1'))
    runner = testing.CliRunner()
    result = runner.invoke(
        stages.create, catch_exceptions=False, input='my_gcp_project')
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(
        result.output,
        textwrap.dedent("""\
            >>>> Create stage
                 Enter your Cloud Project ID: my_gcp_project
                 Allowed to access Project ID "my_gcp_project"
            ---> Configure gcloud with new Project Id ✓
                 Project ID found: my_gcp_project
            ---> Detect env variables
            ---> Activate Cloud services ✓
            ---> Retrieve gcloud current user ✓
            Stage file created: (.*)/my_gcp_project.tfvars.json
            """))


if __name__ == '__main__':
  absltest.main()
