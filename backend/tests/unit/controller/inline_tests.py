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
import freezegun

from controller import inline


class TestFunctions(absltest.TestCase):

  @freezegun.freeze_time("2018-04-01T00:00:00")
  def test_inline_function_today(self):
    func = inline.functions['today']
    self.assertEqual(
        func('%Y-%m-%dT%H:%M:%S%z'),
        '2018-04-01T00:00:00')

  @freezegun.freeze_time("2018-04-01T13:15:00")
  def test_inline_function_days_ago(self):
    func = inline.functions['days_ago']
    days_ago = 3
    self.assertEqual(
        func(days_ago, '%Y-%m-%dT%H:%M:%S%z'),
        '2018-03-29T13:15:00')

  @freezegun.freeze_time("2018-04-01T13:15:00")
  def test_inline_function_hours_ago(self):
    func = inline.functions['hours_ago']
    hours_ago = 5
    self.assertEqual(
        func(hours_ago, '%Y-%m-%dT%H:%M:%S%z'),
        '2018-04-01T08:15:00')

  @freezegun.freeze_time("2018-04-01T00:00:00")
  def test_inline_function_days_since(self):
    func = inline.functions['days_since']
    self.assertEqual(func('2018-03-29', '%Y-%m-%d'), 3)


if __name__ == '__main__':
  absltest.main()
