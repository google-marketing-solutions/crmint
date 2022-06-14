# Copyright 2018 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper methods for testing."""

import subprocess
from typing import Callable
from unittest import mock


def mock_subprocess_result_side_effect(
    user_role: bytes = b'roles/owner',
    billing_account_name: bytes = b'billingAccountName/XXX-YYY',
    billing_enabled: bool = True,
    stdout: bytes = b'output',
    stderr: bytes = b'') -> Callable[[str, ...], mock.Mock]:
  """Returns a method to use as a mock side effect."""
  def _side_effect(cmd, **unused_kwargs):
    mock_result = mock.create_autospec(
        subprocess.CompletedProcess, instance=True)
    mock_result.returncode = 0
    mock_result.stdout = stdout
    mock_result.stderr = stderr
    if '--format="value(bindings.role)"' in cmd:
      mock_result.stdout = user_role
    elif 'billingAccountName' in cmd:
      mock_result.stdout = billing_account_name
    elif 'billingEnabled' in cmd:
      mock_result.stdout = b'True' if billing_enabled else b'False'
    return mock_result
  return _side_effect
