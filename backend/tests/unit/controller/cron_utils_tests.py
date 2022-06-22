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

from absl.testing import absltest
from absl.testing import parameterized
import freezegun

from controller import cron_utils


class TestCronUtils(parameterized.TestCase):

  @parameterized.parameters(
      ('* * * * *', True),
      ('9 * * * *', True),
      ('3,9,25,16 * * * *', True),
      ('3,25,16 * * * *', False),
  )
  @freezegun.freeze_time('2015-06-18T00:09:12')
  def test_cron_on_minutes(self, cron, expected):
    self.assertEqual(
        cron_utils.cron_match(cron),
        expected)

  @parameterized.parameters(
      ('* * * * *', True),
      ('* 16 * * *', True),
      ('6 16 * * *', False),
      ('7 16 * * *', True),
      ('8 16 * * *', False),
      ('* 2,8,16 * * *', True),
      ('3 16 * * *', False),
      ('* 2,8 * * *', False),
  )
  @freezegun.freeze_time('2015-06-18T16:07:19')
  def test_cron_on_hours(self, cron, expected):
    self.assertEqual(
        cron_utils.cron_match(cron),
        expected)

  @parameterized.parameters(
      ('* * * * *', True),
      ('* * 18 * *', True),
      ('* * 1,16,18 * *', True),
      ('* * 19 * *', False),
      ('* * 1,16 * *', False),
      ('* * 1,16 * *', False),
  )
  @freezegun.freeze_time('2015-06-18T16:07:19')
  def test_cron_on_dom(self, cron, expected):
    self.assertEqual(
        cron_utils.cron_match(cron),
        expected)

  @parameterized.parameters(
      ('* * * * *', True),
      ('* * * 6 *', True),
      ('* * * 1,4,6,12 *', True),
      ('* * * 5 *', False),
      ('* * * 1,4,12 *', False),
  )
  @freezegun.freeze_time('2015-06-18T16:07:19')
  def test_cron_on_month(self, cron, expected):
    self.assertEqual(
        cron_utils.cron_match(cron),
        expected)

  @parameterized.parameters(
      ('* * * * *', True),
      ('* * * * 4', True),
      ('* * * * 0,3,4', True),
      ('* * * * 3', False),
      ('* * * * 0,3,6', False),
  )
  @freezegun.freeze_time('2015-06-18T16:07:19')
  def test_cron_on_dow(self, cron, expected):
    self.assertEqual(
        cron_utils.cron_match(cron),
        expected)


if __name__ == '__main__':
  absltest.main()
