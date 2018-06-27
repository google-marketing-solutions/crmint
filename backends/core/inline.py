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

from datetime import datetime
from datetime import timedelta


def _today(format):
  return datetime.today().strftime(format)


def _days_ago(n_days, format):
  dt = datetime.today() - timedelta(int(n_days))
  return dt.strftime(format)


def _hours_ago(n_hours, format):
  dt = datetime.today() - timedelta(0, int(n_hours) * 3600)
  return dt.strftime(format)


def _days_since(date, format):
  return (datetime.today() - datetime.strptime(str(date), format)).days


functions = {
    'today': _today,
    'days_ago': _days_ago,
    'hours_ago': _hours_ago,
    'days_since': _days_since,
}
