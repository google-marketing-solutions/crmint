"""Tests for cli.appcli."""

import textwrap

from absl.testing import absltest
from click import testing

import appcli


class AppCLITest(absltest.TestCase):

  def test_list_commands(self):
    runner = testing.CliRunner()
    result = runner.invoke(appcli.cli, catch_exceptions=False)
    self.assertEqual(result.exit_code, 0, msg=result.output)
    self.assertEqual(
        result.output,
        textwrap.dedent("""\
            Usage: cli [OPTIONS] COMMAND [ARGS]...

              Manage your CRMint instances on GCP or locally.

            Options:
              --version  Print out CRMint version.
              --help     Show this message and exit.

            Commands:
              bundle  Deploys CRMint in one command.
              cloud   Manage your CRMint instance on GCP.
              stages  Manage multiple instances of CRMint.
            """)
    )


if __name__ == '__main__':
  absltest.main()
