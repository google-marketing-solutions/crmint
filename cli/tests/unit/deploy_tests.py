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


import unittest

import commands.deploy
import commands._constants

from click.testing import CliRunner


class TestDeploy(unittest.TestCase):

  def setUp(self):
    super(TestDeploy, self).setUp()

  def tearDown(self):
    super(TestDeploy, self).tearDown()

  def test_cron_stage_not_found(self):
    runner = CliRunner()
    result = runner.invoke(commands.deploy.cron, ['-m', '10', 'stage'])
    self.assertNotEqual(result.exit_code, 0)
    self.assertEqual(result.output, "Stage file not found.\n")
