# Copyright 2020 Google Inc. All rights reserved.
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

"""Legacy worker running SQL queries; please use BQScriptExecutor instead."""


from jobs.workers.bigquery.bq_script_executor import BQScriptExecutor


class BQQueryLauncher(BQScriptExecutor):  # pylint: disable=too-few-public-methods
  """Legacy worker to run SQL queries and store results in tables."""

  PARAMS = [
      ('query', 'sql', True, '', 'SQL query'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('overwrite', 'boolean', True, False, 'Overwrite table'),
  ]

  def _execute(self):
    or_replace = 'OR REPLACE' if self._params['overwrite'] else ''
    table = self._get_full_table_name()
    query = self._params['query'].strip()
    script = f'CREATE {or_replace} TABLE `{table}` AS {query}'
    self._execute_sql_script(script)
