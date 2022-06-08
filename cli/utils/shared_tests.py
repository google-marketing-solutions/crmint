"""Tests for cli.utils.shared."""

import pathlib
import textwrap
from unittest import mock

from absl.testing import absltest
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
                     pathlib.Path(constants.STAGE_DIR, 'foo.py'))
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
    self.assertEqual(result.output, '---> Runs custom command \N{check mark}\n')

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
    # pylint: disable=trailing-whitespace
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            ---> Runs custom command \N{check mark}

            Failed step "Runs custom command"
            command: echo -n "foo=bar" && exit 1
            exit code: 1
            stderr: 
            stdout: foo=bar
            """)
    )
    # pylint: enable=trailing-whitespace

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
            ---> Runs custom command \N{check mark}

            Failed step "Runs custom command"
            command: echo -n "foo=bar" && >&2 echo -n "error details" && exit 1
            exit code: 1
            stderr: error details
            stdout: foo=bar
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
            stderr: None
            stdout: None
            """)
    )


if __name__ == '__main__':
  absltest.main()
