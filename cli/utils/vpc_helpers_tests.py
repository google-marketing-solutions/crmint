"""Tests for cli.utils.vpc_helpers."""

import subprocess
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from cli.utils import shared
from cli.utils import vpc_helpers


class VPCHelpersTests(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    self.enter_context(
        mock.patch.object(
            shared,
            'get_regions',
            autospec=True,
            return_value=('europe-west', 'europe-west1')))
    self.stage = shared.default_stage_context(
        shared.ProjectId('dummy_stage_v3'))

  @parameterized.named_parameters(
      ('VPC', vpc_helpers._check_if_vpc_exists),
      ('Peering', vpc_helpers._check_if_peering_exists),
      ('Subnet Connector', vpc_helpers._check_if_connector_subnet_exists),
      ('VPC Connector', vpc_helpers._check_if_vpc_connector_exists),
  )
  def test_if_check_method_succeeds(self, check_method):
    mock_result = mock.create_autospec(
        subprocess.CompletedProcess, instance=True)
    mock_result.returncode = 0
    mock_result.stdout = b''
    mock_result.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_result))
    self.assertTrue(check_method(self.stage))

  @parameterized.named_parameters(
      ('VPC', vpc_helpers._check_if_vpc_exists),
      ('Peering', vpc_helpers._check_if_peering_exists),
      ('Subnet Connector', vpc_helpers._check_if_connector_subnet_exists),
      ('VPC Connector', vpc_helpers._check_if_vpc_connector_exists),
  )
  def test_if_check_method_fails(self, check_method):
    mock_result = mock.create_autospec(
        subprocess.CompletedProcess, instance=True)
    mock_result.returncode = 1
    mock_result.stdout = b''
    mock_result.stderr = b''
    self.enter_context(
        mock.patch.object(
            subprocess, 'run', autospec=True, return_value=mock_result))
    self.assertFalse(check_method(self.stage))


if __name__ == '__main__':
  absltest.main()
