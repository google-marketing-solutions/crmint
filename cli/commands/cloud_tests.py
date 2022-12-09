"""Tests for cli.commands.cloud."""

import os
import pathlib
import shutil
import subprocess
import tempfile
import textwrap
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
import click
from click import testing

from cli.commands import cloud
from cli.utils import constants
from cli.utils import shared
from cli.utils import test_helpers

DATA_DIR = os.path.join(os.path.dirname(__file__), '../testdata')


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


class CloudChecklistTest(parameterized.TestCase):

  @parameterized.named_parameters(
      ('User not project owner', 'roles/editor', 1),
      ('User is project owner', 'roles/owner', 0),
      ('User has other role is project owner', 'roles/viewer\nroles/owner', 0),
      ('User is project editor with missing roles', 'roles/editor\nroles/viewer', 1),
      ('User is project editor with one missing role', 'roles/editor\nroles/iap.admin\nroles/run.admin\nroles/compute.networkAdmin', 1),
      ('User is project editor with all extra roles', 'roles/editor\nroles/iap.admin\nroles/run.admin\nroles/compute.networkAdmin\nroles/resourcemanager.projectIamAdmin\nroles/secretmanager.admin', 0),
  )
  def test_user_with_different_roles(self, user_role, exit_code):
    side_effect_run = test_helpers.mock_subprocess_result_side_effect(
        user_role=user_role)
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=side_effect_run))
    self.enter_context(
        mock.patch.object(shared, 'fetch_stage_or_default', autospec=True))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.checklist, catch_exceptions=False)
    self.assertEqual(result.exit_code, exit_code, msg=result.output)
    if exit_code == 0:
      self.assertNotIn('Missing IAM roles are: ', result.output)
    else:
      self.assertIn('Missing IAM roles are: ', result.output)

  def test_billing_not_configured(self):
    side_effect_run = test_helpers.mock_subprocess_result_side_effect(
        billing_account_name=b'', billing_enabled=False)
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=side_effect_run))
    self.enter_context(
        mock.patch.object(shared, 'fetch_stage_or_default', autospec=True))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.checklist, catch_exceptions=False)
    self.assertEqual(result.exit_code, 1, msg=result.output)
    self.assertIn('Please configure your billing', result.output)

  def test_billing_not_enabled(self):
    side_effect_run = test_helpers.mock_subprocess_result_side_effect(
        billing_account_name=b'XXX-YYY', billing_enabled=False)
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=side_effect_run))
    self.enter_context(
        mock.patch.object(shared, 'fetch_stage_or_default', autospec=True))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.checklist, catch_exceptions=False)
    self.assertEqual(result.exit_code, 1, msg=result.output)
    self.assertIn('Please enable billing', result.output)

  def test_validates_stdout(self):
    side_effect_run = test_helpers.mock_subprocess_result_side_effect()
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=side_effect_run))
    self.enter_context(
        mock.patch.object(shared, 'fetch_stage_or_default', autospec=True))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.checklist, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            >>>> Checklist
            ---> Retrieve gcloud current user ✓
            ---> Retrieve user IAM roles ✓
            ---> Retrieve billing account name ✓
            ---> Check that billing is enabled ✓
            Done.
            """)
    )


class CloudSetupTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    side_effect_run = test_helpers.mock_subprocess_result_side_effect()
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=side_effect_run))
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='dummy_project_with_vpc'))
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
    shutil.copyfile(
        _datafile('dummy_project_without_vpc.tfvars.json'),
        pathlib.Path(constants.STAGE_DIR, 'dummy_project_without_vpc.tfvars.json'))
    # Uses a temporary directory we can keep a reference to.
    self.tmp_workdir = self.create_tempdir('workdir')
    self.enter_context(
        mock.patch.object(
            tempfile,
            'mkdtemp',
            autospec=True,
            return_value=self.tmp_workdir.full_path))

  def test_fetch_existing_stage(self):
    """Should not raise an exception if stage file exists."""
    stage_path = pathlib.Path(
        constants.STAGE_DIR, 'dummy_project_with_vpc.tfvars.json')
    try:
      stage = shared.fetch_stage_or_default(stage_path)
    except shared.CannotFetchStageError:
      self.fail('Should not raise an exception')

  def test_fetch_stage_suggest_resolution_if_no_stage(self):
    """Should raise an exception inviting the user to create a stage file."""
    runner = testing.CliRunner(mix_stderr=False)
    with runner.isolation() as (out, err):
      stage_path = pathlib.Path(
          constants.STAGE_DIR, 'new_dummy_project.tfvars.json')

      with self.subTest('Raises an exception'):
        with self.assertRaises(shared.CannotFetchStageError):
          shared.fetch_stage_or_default(stage_path)
      with self.subTest('Suggest a resolution path to the user'):
        self.assertIn(b'Fix this by running: $ crmint stages create',
                      out.getvalue())
        self.assertEmpty(err.getvalue())  # pytype: disable=attribute-error

  @parameterized.named_parameters(
      ('Invoked without options', []),
      ('Invoked with --debug', ['--debug']),
  )
  def test_can_run_setup(self, args):
    tf_plan_file = _datafile('tfplan_with_vpc.json')
    with open(tf_plan_file, 'rb') as f:
      tf_plan_content = f.read()
    self.enter_context(
        mock.patch.object(
            cloud,
            'terraform_show_plan',
            autospec=True,
            return_value=tf_plan_content))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, args=args, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)

  def test_validates_stdout_without_vpc(self):
    tf_plan_file = _datafile('tfplan_without_vpc.json')
    with open(tf_plan_file, 'rb') as f:
      tf_plan_content = f.read()
    self.enter_context(
        mock.patch.object(
            cloud,
            'terraform_show_plan',
            autospec=True,
            return_value=tf_plan_content))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(
        result.output,
        textwrap.dedent("""\
            >>>> Setup
                 Project ID found: dummy_project_with_vpc
            ---> Initialize Terraform ✓
            ---> List Terraform workspaces ✓
            ---> Create new Terraform workspace: dummy_project_with_vpc ✓
            ---> Retrieve digest for image: frontend:latest ✓
                 output
            ---> Retrieve digest for image: controller:latest ✓
                 output
            ---> Retrieve digest for image: jobs:latest ✓
                 output
            ---> Generate Terraform plan ✓
                 Cloud Run Service \\(3\\)
                 Cloud Run Service IAM Member \\(3\\)
                 (.|\\n)*
            ---> Apply Terraform plan ✓
            ---> CRMint UI ✓
                 output
            ---> CRMint UI \\(unsecured, temporarily\\) ✓
                 output
            Done.
            """)
    )
    self.assertNotIn('VPC Access Connector (1)', result.output)

  def test_validates_stdout_with_vpc(self):
    tf_plan_file = _datafile('tfplan_with_vpc.json')
    with open(tf_plan_file, 'rb') as f:
      tf_plan_content = f.read()
    self.enter_context(
        mock.patch.object(
            cloud,
            'terraform_show_plan',
            autospec=True,
            return_value=tf_plan_content))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertIn('VPC Access Connector (1)', result.output)


if __name__ == '__main__':
  absltest.main()
