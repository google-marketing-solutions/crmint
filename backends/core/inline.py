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
import os
# from google.cloud import bigquery
# from google.cloud.exceptions import NotFound


_SESSION = None


def open_session():
  global _SESSION
  _SESSION = {'bq_cache': {}}


def close_session():
  global _SESSION
  _SESSION = None


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


# def _bigquery(table_name, field_name):
#   def _get_bq_client():
#     try:
#       return _SESSION['bq_client']
#     except KeyError:
#       key = os.path.join(os.path.dirname(__file__), '..', 'data',
#                          'service-account.json')
#       _SESSION['bq_client'] = bigquery.Client.from_service_account_json(key)
#       return _SESSION['bq_client']
#
#   def _fetch_bq_table_data(table_name):
#     client = _get_bq_client()
#     table_name_pieces = table_name.split('.')
#     if len(table_name_pieces) == 2:
#       dataset_id, table_id = table_name_pieces
#     elif len(table_name_pieces) == 3:
#       project_id, dataset_id, table_id = table_name_pieces
#       client.project = project_id
#     else:
#       raise ValueError('Malformed BigQuery table name: `%s`' % table_name)
#     dataset = client.dataset(dataset_id)
#     table = dataset.table(table_id)
#     try:
#       table.reload()
#     except NotFound:
#       raise ValueError('BigQuery table `%s` not found' % table_name)
#     field_names = [f.name for f in table.schema]
#     filed_values = list(table.fetch_data(max_results=1))[0]
#     _SESSION['bq_cache'][table_name] = dict(zip(field_names, filed_values))
#
#   if table_name not in _SESSION['bq_cache']:
#     _fetch_bq_table_data(table_name)
#   try:
#     value = _SESSION['bq_cache'][table_name][field_name]
#   except KeyError:
#     raise ValueError(
#         "No field '%s' in BigQuery table `%s`" % (field_name, table_name))
#   if isinstance(value, list):
#     return '\n'.join([str(e) for e in value])
#   else:
#     return value


functions = {
    'today': _today,
    'days_ago': _days_ago,
    'hours_ago': _hours_ago,
    'days_since': _days_since,
    # 'bigquery': _bigquery,
}
