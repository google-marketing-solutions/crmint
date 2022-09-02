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
from cli.utils import vpc_helpers

DATA_DIR = os.path.join(os.path.dirname(__file__), '../testdata')

PUBSUB_TOPICS_OUTPUT = textwrap.dedent("""\
    messageStoragePolicy:
      allowedPersistenceRegions:
      - europe-west1
      - us-central1
    name: projects/myproject/topics/crmint-start-task
    ---
    messageStoragePolicy:
      allowedPersistenceRegions:
      - europe-west1
      - us-central1
    name: projects/myproject/topics/crmint-start-pipeline
    """)

PUBSUB_SUBSCRIPTIONS_OUTPUT = textwrap.dedent("""\
    ackDeadlineSeconds: 60
    expirationPolicy: {}
    messageRetentionDuration: 604800s
    name: projects/myproject/subscriptions/crmint-start-pipeline-subscription
    pushConfig:
      attributes:
        x-goog-version: v1
      pushEndpoint: https://myproject.appspot.com/push/start-pipeline?token=ca39175dbde9d587534ffd6c769e0a4e6a0d7570a68d0fd9a4303970c26469be
    retryPolicy:
      maximumBackoff: 600s
      minimumBackoff: 10s
    state: ACTIVE
    topic: projects/myproject/topics/crmint-start-pipeline
    ---
    ackDeadlineSeconds: 600
    expirationPolicy: {}
    messageRetentionDuration: 604800s
    name: projects/myproject/subscriptions/crmint-start-task-subscription
    pushConfig:
      attributes:
        x-goog-version: v1
      pushEndpoint: https://myproject.appspot.com/push/start-task?token=ca39175dbde9d587534ffd6c769e0a4e6a0d7570a68d0fd9a4303970c26469be
    retryPolicy:
      maximumBackoff: 600s
      minimumBackoff: 60s
    state: ACTIVE
    topic: projects/myproject/topics/crmint-start-task
    """)


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


class PubSubHelpersTest(parameterized.TestCase):

  @parameterized.named_parameters(
      ('Topics', 'topics', PUBSUB_TOPICS_OUTPUT,
       ['crmint-start-pipeline', 'crmint-start-task']),
      ('Subscriptions', 'subscriptions', PUBSUB_SUBSCRIPTIONS_OUTPUT,
       ['crmint-start-pipeline-subscription', 'crmint-start-task-subscription'])
  )
  def test_get_existing_pubsub_topics(self, entity_name, cmd_output, entities):
    mock_result = mock.create_autospec(
        subprocess.CompletedProcess, instance=True)
    mock_result.returncode = 0
    mock_result.stdout = cmd_output
    mock_result.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_result))
    stage = shared.default_stage_context(shared.ProjectId('foo'))
    self.assertCountEqual(
        cloud._get_existing_pubsub_entities(stage, entity_name),
        entities)


class CloudChecklistTest(parameterized.TestCase):

  @parameterized.named_parameters(
      ('User not project owner', 'roles/editor', 1),
      ('User is project owner', 'roles/owner', 0),
      ('User is project owner has other role', 'roles/owner\nroles/viewer', 0),
      ('User has other role is project owner', 'roles/viewer\nroles/owner', 0),
  )
  def test_user_not_project_owner(self, user_role, exit_code):
    side_effect_run = test_helpers.mock_subprocess_result_side_effect(
        user_role=user_role)
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=side_effect_run))
    self.enter_context(
        mock.patch.object(cloud, 'fetch_stage_or_default', autospec=True))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.checklist, catch_exceptions=False)
    self.assertEqual(result.exit_code, exit_code, msg=result.output)
    if exit_code == 0:
      self.assertNotIn('Missing roles/owner for user', result.output)
    else:
      self.assertIn('Missing roles/owner for user', result.output)

  def test_billing_not_configured(self):
    side_effect_run = test_helpers.mock_subprocess_result_side_effect(
        billing_account_name=b'', billing_enabled=False)
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, side_effect=side_effect_run))
    self.enter_context(
        mock.patch.object(cloud, 'fetch_stage_or_default', autospec=True))
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
        mock.patch.object(cloud, 'fetch_stage_or_default', autospec=True))
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
        mock.patch.object(cloud, 'fetch_stage_or_default', autospec=True))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.checklist, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            >>>> Checklist
            ---> Retrieve gcloud current user ✓
            ---> Getting project number ✓
            ---> Validates current user has roles/owner ✓
            ---> Retrieve billing account name ✓
            ---> Check that billing is enabled ✓
            Done.
            """)
    )


class CloudBaseTest(parameterized.TestCase):

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
            return_value='dummy_stage_v3'))
    # `create_tempfile` needs access to --test_tmpdir, however in the OSS world
    # pytest doesn't run `absltest.main`, so we need to init flags ourselves.
    test_helpers.initialize_flags_with_defaults()
    # Overrides the default stage directory with a custom temporary directory.
    tmp_stage_dir = self.create_tempdir('stage_dir')
    self.enter_context(
        mock.patch.object(constants, 'STAGE_DIR', tmp_stage_dir.full_path))
    shutil.copyfile(_datafile('dummy_stage_v2.py'),
                    pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v2.py'))
    shutil.copyfile(_datafile('dummy_stage_v3.py'),
                    pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v3.py'))
    # Uses a temporary directory we can keep a reference to.
    self.tmp_workdir = self.create_tempdir('workdir')
    self.enter_context(
        mock.patch.object(
            tempfile,
            'mkdtemp',
            autospec=True,
            return_value=self.tmp_workdir.full_path))


class CloudSetupTest(CloudBaseTest):

  @parameterized.named_parameters(
      ('Invoked without options', []),
      ('Invoked with --debug', ['--debug']),
  )
  def test_can_run_deploy(self, args):
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, args=args, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)

  def test_validates_stdout_without_vpc(self):
    self.enter_context(
        mock.patch.object(
            vpc_helpers,
            '_check_if_vpc_exists',
            autospec=True,
            return_value=False))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(
        result.output,
        textwrap.dedent("""\
            >>>> Setup
                 Project ID found: dummy_stage_v3
            ---> Activate Cloud services ✓
            ---> Check if App Engine app already exists ✓
            (.|\\n)*
            Done.
            """)
    )

  def test_validates_stdout_with_vpc(self):
    shutil.copyfile(_datafile('dummy_stage_v3_with_vpc.py'),
                    pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v3.py'))
    self.enter_context(
        mock.patch.object(
            vpc_helpers,
            '_check_if_vpc_exists',
            autospec=True,
            return_value=False))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(
        result.output,
        textwrap.dedent("""\
            >>>> Setup
                 Project ID found: dummy_stage_v3
            ---> Activate Cloud services ✓
            ---> Create the VPC ✓
            ---> Allocating an IP address range ✓
            ---> Check if VPC Peering exists ✓
            ---> Updating the private connection ✓
            ---> Check if VPC Subnet already exists ✓
                 VPC Connector Subnet already exists.
            ---> Check if VPC Connector already exists ✓
                 VPC Connector already exists.
            ---> Check if App Engine app already exists ✓
            (.|\\n)*
            Done.
            """)
    )

  def test_validates_stdout_with_existing_vpc(self):
    shutil.copyfile(_datafile('dummy_stage_v3_with_vpc.py'),
                    pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v3.py'))
    self.enter_context(
        mock.patch.object(
            vpc_helpers,
            '_check_if_vpc_exists',
            autospec=True,
            return_value=True))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(result.output, 'VPC already exists.')

  def test_validates_stdout_with_no_vpc_peerings(self):
    shutil.copyfile(_datafile('dummy_stage_v3_with_vpc.py'),
                    pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v3.py'))
    self.enter_context(
        mock.patch.object(
            vpc_helpers,
            '_check_if_peering_exists',
            autospec=True,
            return_value=False))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(result.output, '---> Creating the private connection')

  def test_validates_stdout_updating_tokens(self):
    shutil.copyfile(_datafile('dummy_stage_v3_with_vpc.py'),
                    pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v3.py'))
    self.enter_context(
        mock.patch.object(
            cloud,
            '_get_existing_pubsub_entities',
            autospec=True,
            return_value=['crmint-start-task-subscription']))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.setup, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(
        result.output,
        textwrap.dedent("""\
            ---> Updating subscription token ✓
                 Token updated for subscription crmint-start-task-subscription
            """)
    )
    self.assertRegex(
        result.output,
        '---> Creating PubSub subscription crmint-task-finished-subscription ✓',
    )

  def test_validates_stdout_on_grant_required_permissions(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_regions',
            autospec=True,
            return_value=('us-central', 'us-central1')))
    self.enter_context(
        mock.patch.object(
            cloud, 'get_project_number', autospec=True, return_value='123'))
    stage = shared.default_stage_context(shared.ProjectId('foo'))

    @click.command('custom')
    def _custom_command() -> None:
      cloud._grant_required_permissions(stage)

    runner = testing.CliRunner()
    result = runner.invoke(
        _custom_command, standalone_mode=False, catch_exceptions=False)
    # Our command wrapper should not fail, exit_code should be 0 and report the
    # error on the standard output.
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertStartsWith(
        result.output,
        '---> Grant required permissions (1/',
        msg='Ensures that the first granting permission index starts at 1.'
    )


class CloudDeployTest(CloudBaseTest):

  def test_fetch_stage_or_default_no_exception_for_latest_spec(self):
    """Should raise an exception inviting the user to migrate."""
    stage_path = pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v3.py')
    try:
      stage = cloud.fetch_stage_or_default(stage_path)
    except cloud.CannotFetchStageError:
      self.fail('Should not raise an exception on latest spec')
    self.assertEqual(stage.spec_version, 'v3.0')

  def test_fetch_stage_or_default_on_old_spec_version(self):
    """Should raise an exception inviting the user to migrate."""
    runner = testing.CliRunner(mix_stderr=False)
    with runner.isolation() as (out, err):
      stage_path = pathlib.Path(constants.STAGE_DIR, 'dummy_stage_v2.py')

      with self.subTest('Raises an exception'):
        with self.assertRaises(cloud.CannotFetchStageError):
          cloud.fetch_stage_or_default(stage_path)
      with self.subTest('Suggest a resolution path to the user'):
        self.assertIn(b'Fix this by running: $ crmint stages migrate',
                      out.getvalue())
        self.assertEmpty(err.getvalue())

  @parameterized.named_parameters(
      ('Invoked without options', []),
      ('Invoked with --debug', ['--debug']),
  )
  def test_can_run_deploy(self, args):
    runner = testing.CliRunner()
    result = runner.invoke(cloud.deploy, args=args, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)

  def test_validates_stdout(self):
    runner = testing.CliRunner()
    result = runner.invoke(cloud.deploy, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertRegex(
        result.output,
        textwrap.dedent("""\
            >>>> Deploy
                 Project ID found: dummy_stage_v3
            (.|\\n)*
            ---> CRMint UI ✓
                 output
            Done.
            """)
    )
    self.assertIn('Working directory: ', result.output)
    self.assertIn('---> Deploy frontend service', result.output)
    self.assertIn('---> Deploy controller service', result.output)
    self.assertIn('---> Deploy jobs service', result.output)
    self.assertIn('---> Deploy dispatch rules', result.output)

  def test_validates_app_data_content(self):
    runner = testing.CliRunner()
    result = runner.invoke(cloud.deploy, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    app_filepath = pathlib.Path(self.tmp_workdir.full_path,
                                'backend/data/app.json')
    with open(app_filepath, 'r') as f:
      content = f.read()
      self.assertIn('GAE_APP_TITLE', content)
      self.assertIn('NOTIF_SENDER_EMAIL', content)

  def test_validates_environment_content(self):
    runner = testing.CliRunner()
    result = runner.invoke(cloud.deploy, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    env_filepath = pathlib.Path(self.tmp_workdir.full_path,
                                'frontend/src/environments/environment.prod.ts')
    with open(env_filepath, 'r') as f:
      content = f.read()
      self.assertIn('GAE_APP_TITLE', content)

  def test_unretriable_error(self):
    self.enter_context(
        mock.patch.object(
            cloud,
            '_run_frontend_deployment',
            autospec=True,
            return_value=[1, '', 'Error: Random unretriable error.']))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.deploy, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertNotIn(
        'Detected retriable error. Retrying deployment.',
        result.output)

  def test_retriable_p4sa_error(self):
    self.enter_context(
        mock.patch.object(
            cloud,
            '_run_frontend_deployment',
            autospec=True,
            return_value=[1, '', 'Error: Unable to retrieve P4SA on GAE.']))
    runner = testing.CliRunner()
    result = runner.invoke(cloud.deploy, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertIn(
        'Detected retriable error. Retrying deployment.',
        result.output)


if __name__ == '__main__':
  absltest.main()
