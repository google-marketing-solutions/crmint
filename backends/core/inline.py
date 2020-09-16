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

from datetime import datetime, timedelta
from google.cloud import bigquery
from google.cloud.exceptions import NotFound


_SESSION = None


def open_session():
  global _SESSION  # pylint: disable=global-statement
  _SESSION = {'bq_cache': {}}


def close_session():
  global _SESSION  # pylint: disable=global-statement
  _SESSION = None


def _today(datetime_format):
  return datetime.today().strftime(datetime_format)


def _days_ago(n_days, datetime_format):
  dt = datetime.today() - timedelta(int(n_days))
  return dt.strftime(datetime_format)


def _hours_ago(n_hours, datetime_format):
  dt = datetime.today() - timedelta(0, int(n_hours) * 3600)
  return dt.strftime(datetime_format)


def _days_since(date, datetime_format):
  return (datetime.today() - datetime.strptime(str(date), datetime_format)).days


def _bigquery(table_id, field_name):
  def _get_bq_client():
    try:
      return _SESSION['bq_client']
    except KeyError:
      _SESSION['bq_client'] = bigquery.Client()
      return _SESSION['bq_client']

  def _fetch_bq_table_data(table_id):
    client = _get_bq_client()
    try:
      rows = client.list_rows(table_id, max_results=1)
    except NotFound as e:
      raise ValueError(f'BigQuery table `{table_id}` not found') from e
    try:
      row = next(iter(rows))
    except StopIteration as e:
      raise ValueError(f'BigQuery table `{table_id}` is empty') from e
    _SESSION['bq_cache'][table_id] = dict(row.items())

  if table_id not in _SESSION['bq_cache']:
    _fetch_bq_table_data(table_id)
  try:
    value = _SESSION['bq_cache'][table_id][field_name]
  except KeyError as e:
    raise ValueError(
        f"No field '{field_name}' in BigQuery table `{table_id}`") from e
  if isinstance(value, list):
    return '\n'.join([str(e) for e in value])
  return value


functions = {
    'today': _today,
    'days_ago': _days_ago,
    'hours_ago': _hours_ago,
    'days_since': _days_since,
    'bigquery': _bigquery,
}
