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
import imp
from unittest import TestCase
from shutil import copyfile
import mock
from click.testing import CliRunner

import crmint_commands.deploy
from crmint_commands.utils import constants


class TestDeploy(TestCase):

  def setUp(self):
    super(TestDeploy, self).setUp()

  def tearDown(self):
    super(TestDeploy, self).tearDown()

  @staticmethod
  def _get_mocked_stage(mocked_stage_name, mocked_path,
                        stage_example_path=constants.STAGE_EXAMPLE_PATH):
    copyfile(stage_example_path, "{}.py".format(mocked_stage_name))
    mocked_stage = imp.load_source(mocked_stage_name,
                                   "{}.py".format(mocked_stage_name))
    mocked_stage.workdir = mocked_path
    return mocked_stage

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_frontend_succeeded(self, mocked_get_stage_object, mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      mocked_get_stage_object.return_value = TestDeploy._get_mocked_stage(mocked_stage_name,
                                                                          os.getcwd())
    result = runner.invoke(crmint_commands.deploy.frontend, [mocked_stage_name])
    self.assertEqual(result.exit_code, 0)

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_ibackend_succeeded(self, mocked_get_stage_object, mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      mocked_get_stage_object.return_value = TestDeploy._get_mocked_stage(mocked_stage_name,
                                                                          os.getcwd())
    result = runner.invoke(crmint_commands.deploy.ibackend, [mocked_stage_name])
    self.assertEqual(result.exit_code, 0)

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_jbackend_succeeded(self, mocked_get_stage_object, mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      mocked_get_stage_object.return_value = TestDeploy._get_mocked_stage(mocked_stage_name,
                                                                          os.getcwd())
    result = runner.invoke(crmint_commands.deploy.jbackend, [mocked_stage_name])
    self.assertEqual(result.exit_code, 0)

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_cron_minutes_succeeded(self, mocked_get_stage_object,
                                  mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_cron_file_name = "mocked_cron.yaml"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      with mock.patch('crmint_commands.utils.constants.CRON_FILE',
                      mocked_cron_file_name):
        mocked_workdir = os.path.join(os.getcwd(), "workdir")
        mocked_stage = TestDeploy._get_mocked_stage(mocked_stage_name,
                                                    mocked_workdir)
        mocked_get_stage_object.return_value = mocked_stage
        result = runner.invoke(crmint_commands.deploy.cron, [mocked_stage_name, '-m 9'])
        self.assertEqual(result.exit_code, 0)
        with open(mocked_cron_file_name, "r") as cron_file:
          self.assertIn("9 minutes", cron_file.read())

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_cron_hours_succeeded(self, mocked_get_stage_object,
                                mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_cron_file_name = "mocked_cron.yaml"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      with mock.patch('crmint_commands.utils.constants.CRON_FILE',
                      mocked_cron_file_name):
        mocked_workdir = os.path.join(os.getcwd(), "workdir")
        mocked_stage = TestDeploy._get_mocked_stage(mocked_stage_name,
                                                    mocked_workdir)
        mocked_get_stage_object.return_value = mocked_stage
        result = runner.invoke(crmint_commands.deploy.cron,
                               [mocked_stage_name, '-h 12'])
        self.assertEqual(result.exit_code, 0)
        with open(mocked_cron_file_name, "r") as cron_file:
          self.assertIn("12 hours", cron_file.read())

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_cron_with_minutes_and_hours_options_fails(self, mocked_get_stage_object,
                                                     mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_cron_file_name = "mocked_cron.yaml"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      with mock.patch('crmint_commands.utils.constants.CRON_FILE',
                      mocked_cron_file_name):
        mocked_stage = TestDeploy._get_mocked_stage(mocked_stage_name,
                                                    os.getcwd())
        mocked_get_stage_object.return_value = mocked_stage
        result = runner.invoke(crmint_commands.deploy.cron,
                               [mocked_stage_name, '-m 10', '-h 12'])
        self.assertEqual(result.exit_code, 1)

  @mock.patch('crmint_commands.deploy._check_stage_file')
  def test_cron_stage_not_found(self, mocked_check_stage_file):
    mocked_stage = 'random_stage'
    mocked_check_stage_file.return_value = False
    runner = CliRunner()
    result = runner.invoke(crmint_commands.deploy.cron, [mocked_stage, '-m 10'])
    self.assertEqual(result.exit_code, 1)
    self.assertEqual(result.output, "\nStage file '%s' not found.\n" % mocked_stage)

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_migration_with_service_account_success(self, mocked_get_stage_object,
                                                  mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_service_account = "mocked.json"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      mocked_path = os.getcwd()
      mocked_service_account_file_name = "mocked_service_account"
      with mock.patch('crmint_commands.utils.constants.SERVICE_ACCOUNT_PATH',
                      mocked_path):
        with open(constants.SERVICE_ACCOUNT_DEFAULT_FILE_NAME, "w+") as sa:
          sa.write("")
        mocked_stage = TestDeploy._get_mocked_stage(mocked_stage_name, mocked_path)
        mocked_get_stage_object.return_value = mocked_stage
        result = runner.invoke(crmint_commands.deploy.migration,
                               [mocked_stage_name,
                                '-use_service_account'])
        self.assertEqual(result.exit_code, 0)

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_migration_without_service_account_success(self, mocked_get_stage_object,
                                                     mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_service_account = "mocked.json"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      mocked_path = os.getcwd()
      mocked_service_account_file_name = "mocked_service_account.json"
      with mock.patch('crmint_commands.utils.constants.SERVICE_ACCOUNT_PATH',
                      mocked_path),\
          mock.patch('crmint_commands.utils.constants.SERVICE_ACCOUNT_DEFAULT_FILE_NAME',
                     mocked_service_account_file_name):
        with open(mocked_service_account_file_name, "w+") as sa:
          sa.write("")
        mocked_stage = TestDeploy._get_mocked_stage(mocked_stage_name,
                                                    mocked_path)
        mocked_get_stage_object.return_value = mocked_stage
        result = runner.invoke(crmint_commands.deploy.migration,
                               [mocked_stage_name])
        self.assertEqual(result.exit_code, 0)

  @mock.patch('crmint_commands.deploy._check_stage_file')
  @mock.patch('crmint_commands.deploy._get_stage_object')
  def test_reset_pipeline_succeeds(self, mocked_get_stage_object,
                                   mocked_check_stage_file):
    mocked_stage_name = "mocked_stage"
    mocked_check_stage_file.return_value = True
    runner = CliRunner()
    with runner.isolated_filesystem():
      mocked_path = os.getcwd()
      mocked_workdir = os.path.join(os.getcwd(), "workdir")
      mocked_task_name = "mocked_reset_pipeline.py"
      mocked_service_account_file_name = "mocked_service_account.json"
      with mock.patch('crmint_commands.utils.constants.TASKS_PATH',
                      mocked_path),\
           mock.patch('crmint_commands.utils.constants.RESET_PIPELINE_TASK',
                      mocked_task_name):
        with open(mocked_task_name, "w+") as mocked_task:
          mocked_task.write("")
        mocked_stage = TestDeploy._get_mocked_stage(mocked_stage_name,
                                                    mocked_workdir)
        mocked_get_stage_object.return_value = mocked_stage
        result = runner.invoke(crmint_commands.deploy.reset_pipeline,
                               [mocked_stage_name, '-v'])
        self.assertEqual(result.exit_code, 0)
