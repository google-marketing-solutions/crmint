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

from unittest import mock

from absl.testing import absltest

from controller import ads_auth_code
from controller import models
from tests import controller_utils


class TestViews(controller_utils.ControllerAppTest):

  def test_retrieve_configuration(self):
    response = self.client.get('/api/configuration')
    self.assertEqual(response.status_code, 200)

  def test_update_global_variable(self):
    payload = {
        'variables': [
            {
                'name': 'foo',
                'type': 'string',
                'value': 'bar',
            }
        ]
    }
    self.assertEmpty(models.Param.all())
    response = self.client.put('/api/global_variables', json=payload)
    self.assertEqual(response.status_code, 200)
    self.assertLen(models.Param.all(), 1)

  def test_update_general_settings_ads_token(self):
    self.enter_context(
        mock.patch.object(
            ads_auth_code,
            'get_token',
            autospec=True,
            return_value='new-token'))
    payload = {
        'settings': [
            {
                'name': 'google_ads_authentication_code',
                'type': 'string',
                'value': 'foo',
            },
            {
                'name': 'google_ads_refresh_token',
                'type': 'string',
                'value': 'old-token',
            },
        ]
    }
    response = self.client.put('/api/general_settings', json=payload)
    self.assertEqual(response.status_code, 200)
    ads_code_setting = models.GeneralSetting.where(
        name='google_ads_authentication_code').first()
    self.assertEqual(ads_code_setting.value, '')
    ads_token_setting = models.GeneralSetting.where(
        name='google_ads_refresh_token').first()
    self.assertEqual(ads_token_setting.value, 'new-token')

  def test_reset_statuses_expect_post(self):
    response = self.client.get('/api/reset/statuses')
    self.assertEqual(response.status_code, 405)

  def test_can_reset_statuses(self):
    response = self.client.post('/api/reset/statuses')
    self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
  absltest.main()
