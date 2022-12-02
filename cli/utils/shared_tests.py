"""Tests for cli.utils.shared."""

import pathlib
import subprocess
import textwrap
from typing import Tuple
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
import click
from click import testing


from cli.utils import constants
from cli.utils import shared


class SharedTests(absltest.TestCase):

  def test_get_default_stage_path(self):
    self.enter_context(
        mock.patch.object(
            shared,
            'get_current_project_id',
            autospec=True,
            return_value='foo'))
    self.enter_context(
        mock.patch.object(constants, 'STAGE_DIR', '/temporary/stage/dir/'))
    patched_click_echo = self.enter_context(
        mock.patch.object(click, 'echo', autospec=True))
    self.assertEqual(shared.get_default_stage_path(),
                     pathlib.Path(constants.STAGE_DIR, 'foo.tfvars.json'))
    self.assertSequenceEqual(
        patched_click_echo.mock_calls,
        [mock.call('     Project ID found: foo')]
    )

  def test_execute_command_no_error(self):

    @click.command('custom')
    def _custom_command():
      cmd = 'echo -n "foo=bar" && exit 0'
      shared.execute_command('Runs custom command', cmd)

    runner = testing.CliRunner()
    result = runner.invoke(_custom_command, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(result.output, '---> Runs custom command ✓\n')

  def test_execute_command_report_on_empty_errors_by_default(self):

    @click.command('custom')
    def _custom_command():
      cmd = 'echo -n "foo=bar" && exit 1'
      shared.execute_command('Runs custom command', cmd)

    runner = testing.CliRunner()
    result = runner.invoke(_custom_command, catch_exceptions=False)
    # Our command wrapper should not fail, exit_code should be 0 and report the
    # error on the standard output.
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Runs custom command ✓

            Failed step "Runs custom command"
            command: echo -n "foo=bar" && exit 1
            exit code: 1
            stderr:
              <EMPTY>
            stdout:
              foo=bar
            """)
    )

  def test_execute_command_reports_non_empty_errors(self):

    @click.command('custom')
    def _custom_command():
      cmd = 'echo -n "foo=bar" && >&2 echo -n "error details" && exit 1'
      shared.execute_command('Runs custom command', cmd, report_empty_err=False)

    runner = testing.CliRunner()
    result = runner.invoke(_custom_command, catch_exceptions=False)
    # Our command wrapper should not fail, exit_code should be 0 and report the
    # error on the standard output.
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Runs custom command ✓

            Failed step "Runs custom command"
            command: echo -n "foo=bar" && >&2 echo -n "error details" && exit 1
            exit code: 1
            stderr:
              error details
            stdout:
              foo=bar
            """)
    )

  def test_execute_command_in_debug_mode(self):
    """Ensures that stdout is not captured by our tool."""

    @click.command('custom')
    def _custom_command():
      cmd = 'echo -n "foo=bar" && exit 0'
      shared.execute_command('Runs custom command', cmd, debug=True)

    runner = testing.CliRunner()
    result = runner.invoke(_custom_command, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Runs custom command
            cwd: .
            $ echo -n "foo=bar" && exit 0
            """)
    )

  def test_execute_command_reporting_errors_in_debug_mode(self):
    """Ensures that stderr is not captured by our tool."""

    @click.command('custom')
    def _custom_command():
      cmd = 'echo "foo=bar" && >&2 echo -n "error details" && exit 1'
      shared.execute_command('Runs custom command', cmd, debug=True)

    runner = testing.CliRunner(mix_stderr=False)
    result = runner.invoke(_custom_command, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Runs custom command
            cwd: .
            $ echo "foo=bar" && >&2 echo -n "error details" && exit 1

            Failed step "Runs custom command"
            command: echo "foo=bar" && >&2 echo -n "error details" && exit 1
            exit code: 1
            stderr:
              <EMPTY>
            stdout:
              <EMPTY>
            """)
    )

  def test_execute_command_debug_without_std_out(self):
    """Ensures that stdout is captured if `debug_uses_std_out=False`."""

    @click.command('custom')
    def _custom_command():
      cmd = 'echo "foo=bar" && exit 0'
      shared.execute_command(
          'Runs custom command', cmd, debug=True, debug_uses_std_out=False)

    runner = testing.CliRunner(mix_stderr=False)
    result = runner.invoke(_custom_command, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Runs custom command
            cwd: .
            $ echo "foo=bar" && exit 0
            stdout:
              foo=bar

            """)
    )

  def test_execute_command_with_captured_outputs(self):

    @click.command('custom')
    def _custom_command() -> Tuple[int, str, str]:
      cmd = 'echo -n "foo=bar" && >&2 echo -n "error details" && exit 1'
      return shared.execute_command(
          'Runs custom command', cmd, capture_outputs=True)

    runner = testing.CliRunner()
    result = runner.invoke(_custom_command, standalone_mode=False)
    # Our command wrapper should not fail, exit_code should be 0 and report the
    # error on the standard output.
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Runs custom command ✓
            """)
    )
    self.assertSequenceEqual(
        result.return_value,
        [1, 'foo=bar', 'error details']
    )

  def test_execute_command_debug_over_captured_outputs(self):

    @click.command('custom')
    def _custom_command() -> Tuple[int, str, str]:
      cmd = 'echo -n "foo=bar" && >&2 echo -n "error details" && exit 1'
      return shared.execute_command(
          'Runs custom command',
          cmd,
          capture_outputs=True,
          debug=True,
          debug_uses_std_out=False)

    runner = testing.CliRunner()
    result = runner.invoke(_custom_command, standalone_mode=False)
    # Our command wrapper should not fail, exit_code should be 0 and report the
    # error on the standard output.
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Runs custom command
            cwd: .
            $ echo -n "foo=bar" && >&2 echo -n "error details" && exit 1

            Failed step "Runs custom command"
            command: echo -n "foo=bar" && >&2 echo -n "error details" && exit 1
            exit code: 1
            stderr:
              error details
            stdout:
              foo=bar
            """)
    )
    self.assertSequenceEqual(
        result.return_value,
        [1, 'foo=bar', 'error details']
    )


class ProjectIdTests(absltest.TestCase):

  def test_get_current_project_id_configured(self):
    output_bytes = 'my_gcp_project\n'.encode('utf-8')
    mock_run = mock.create_autospec(subprocess.CompletedProcess, instance=True)
    mock_run.returncode = 0
    mock_run.stdout = output_bytes
    mock_run.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_run))
    self.assertEqual(shared.get_current_project_id(), 'my_gcp_project')

  def test_get_current_project_id_unconfigured(self):
    output_bytes = '\n'.encode('utf-8')
    mock_run = mock.create_autospec(subprocess.CompletedProcess, instance=True)
    mock_run.returncode = 0
    mock_run.stdout = output_bytes
    mock_run.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_run))
    self.assertEqual(shared.get_current_project_id(), '')

  def test_list_user_project_ids(self):
    output_bytes = 'other_gcp_project\nmy_gcp_project\n'.encode('utf-8')
    mock_run = mock.create_autospec(subprocess.CompletedProcess, instance=True)
    mock_run.returncode = 0
    mock_run.stdout = output_bytes
    mock_run.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_run))
    self.assertCountEqual(shared.list_user_project_ids(),
                          ['other_gcp_project', 'my_gcp_project'])

  def test_select_project_id(self):
    mock_run = mock.create_autospec(subprocess.CompletedProcess, instance=True)
    mock_run.returncode = 0
    mock_run.stdout = b''
    mock_run.stderr = b''
    patched_run = self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_run))
    shared.select_project_id(shared.ProjectId('gcp_id'))
    patched_run.assert_called_once()


class GetRegionTests(absltest.TestCase):

  def setUp(self):
    super().setUp()
    list_of_regions_bytes = textwrap.dedent("""\
        asia-east1
        asia-northeast1
        asia-southeast1
        australia-southeast1
        europe-west1
        europe-west2
        europe-west3
        us-central1
        us-east1
        us-east4
        us-west1
        us-west2
        us-west3
        us-west4""").encode('utf-8')
    mock_result = mock.create_autospec(
        subprocess.CompletedProcess, instance=True)
    mock_result.returncode = 0
    mock_result.stdout = list_of_regions_bytes
    mock_result.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess,
            'run',
            autospec=True,
            return_value=mock_result))
    self.enter_context(
        mock.patch.object(click, 'prompt', autospec=True, return_value=4))

  def test_get_region(self):
    self.assertEqual(shared.get_region(), 'australia-southeast1')

  def test_stdout(self):

    @click.command('custom')
    def _custom_command():
      shared.get_region()

    runner = testing.CliRunner(mix_stderr=False)
    result = runner.invoke(_custom_command, catch_exceptions=False)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Get available Compute regions ✓
                 1) asia-east1
                 2) asia-northeast1
                 3) asia-southeast1
                 4) australia-southeast1
                 5) europe-west1
                 6) europe-west2
                 7) europe-west3
                 8) us-central1
                 9) us-east1
                 10) us-east4
                 11) us-west1
                 12) us-west2
                 13) us-west3
                 14) us-west4
            """)
    )


class TagsAndVersionsHelpersTests(parameterized.TestCase):

  @parameterized.named_parameters(
      ('No tags', [], []),
      ('No versions', ['foo', 'bar'], []),
      ('Removes non-versions', ['foo-3.0.0', '3.0.0', '4.0'], ['3.0.0', '4.0']),
  )
  def test_filters_versions_from_list_of_tags(self, tags, expected_versions):
    versions = shared.filter_versions_from_tags(tags)
    self.assertSequenceEqual(versions, expected_versions)


if __name__ == '__main__':
  absltest.main()
