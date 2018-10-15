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


import os
from unittest import TestCase
import mock
from click.testing import CliRunner

import crmint_commands.deploy
import crmint_commands._constants



def get_mocked_stage(mocked_path, example_path=crmint_commands._constants.STAGE_EXAMPLE_PATH):
  mocked_stage = crmint_commands.deploy._get_stage_object(example_path)
  mocked_stage["workdir"] = mocked_path
  return mocked_stage

class TestDeploy(TestCase):

  def setUp(self):
    super(TestDeploy, self).setUp()

  def tearDown(self):
    super(TestDeploy, self).tearDown()

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_frontend_succeeded(self, mocked_get_stage_object, mocked_check_stage_file):
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      mocked_stage = get_mocked_stage(os.getcwd())
      mocked_get_stage_object.return_value = mocked_stage
    result = runner.invoke(crmint_commands.deploy.frontend, ['mocked_stage_name'])
    self.assertEqual(result.exit_code, 0)

  def test_cron_stage_not_found(self):
    runner = CliRunner()
    new_stage = 'random_stage'
    result = runner.invoke(crmint_commands.deploy.cron, ['-m', '10', new_stage])
    self.assertNotEqual(result.exit_code, 0)
    self.assertEqual(result.output, "\nStage file '%s' not found.\n" % new_stage)
