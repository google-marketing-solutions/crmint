# Copyright 2023 Google Inc
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

"""MlModel bigquery helpers."""

import dataclasses
from typing import Any
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from controller.ml_model.shared import Source


@dataclasses.dataclass
class Parameter:
  """Represents a variable parameter."""
  key: str
  value_type: str

  def __post_init__(self):
    self.value_type = self.value_type.lower()


@dataclasses.dataclass
class Variable:
  """Represents a single variable (used for feature/label selection)."""
  name: str
  source: str
  count: int
  parameters: list[Parameter]


class CustomClient(bigquery.Client):
  """BigQuery client wrapper that adds custom methods for easy access to necessary data."""

  def __init__(self, location: str) -> None:
    super().__init__(location=location)

  def get_analytics_variables(self,
                              dataset: str,
                              start: int,
                              end: int) -> list[Variable]:
    """Get approximate counts for all GA4 events timeboxed by start and end days.

    Args:
      dataset_name: The dataset where the GA4 events tables are located.
      start_day: The number of days ago from today to start looking for
                 variables.
      end_day: The number of days ago from today to stop looking for variables.

    Returns:
      A list of variables to be used for feature and label selection.
    """

    variables: list[Variable] = []

    augmented_end = start - 90 if start - end > 90 else end

    event_exclude_list = self._quoted_list([
        'user_engagement',
        'scroll',
        'session_start',
        'first_visit',
        'page_view'])

    key_exclude_list = self._quoted_list([
        'debug_mode',
        'ga_session_id',
        'ga_session_number',
        'transaction_id',
        'page_location',
        'page_referrer',
        'session_engaged',
        'engaged_session_event',
        'content_group',
        'engagement_time_msec'])

    query = f"""
      CREATE TEMP TABLE temp__counts(event_name STRING, event_count INT64) AS (
        SELECT
          c.value AS event_name,
          c.count AS event_count
        FROM (
          SELECT APPROX_TOP_COUNT(event_name, 100) AS event_counts
          FROM `{self.project}.{dataset}.events_*`
          WHERE _TABLE_SUFFIX BETWEEN
            FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {start} DAY)) AND
            FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {end} DAY))
          AND event_name NOT IN ({event_exclude_list})
        ), UNNEST(event_counts) AS c
      );

      SELECT
        c.event_name AS name,
        c.event_count AS count,
        p.key AS parameter_key,
        STRING_AGG(
          DISTINCT
          CASE
            WHEN p.value.string_value IS NOT NULL THEN 'string'
            WHEN p.value.int_value IS NOT NULL THEN 'int'
            WHEN p.value.double_value IS NOT NULL THEN 'double'
            WHEN p.value.float_value IS NOT NULL THEN 'float'
            ELSE NULL
          END
        ) AS parameter_value_type
      FROM `{self.project}.{dataset}.events_*` e,
      UNNEST(event_params) AS p
      JOIN temp__counts c
        ON e.event_name = c.event_name
      WHERE _TABLE_SUFFIX BETWEEN
        FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {start} DAY)) AND
        FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {augmented_end} DAY))
      AND p.key NOT IN ({key_exclude_list})
      GROUP BY 1,2,3
      HAVING parameter_value_type IS NOT NULL
      ORDER BY
        count ASC, # reversed to speed up data transformation step
        name ASC,
        parameter_key ASC;
    """
    try:
      job = self.query(query=query)
      events = job.result()
    except NotFound:
      return variables

    for event in events:
      if event.name not in event_exclude_list:
        existing_variable = next(
            (v for v in variables if v.name == event.name), None)
        parameter = Parameter(event.parameter_key, event.parameter_value_type)

        if not existing_variable:
          variable = Variable(
              event.name, Source.GOOGLE_ANALYTICS, event.count, [])
          variable.parameters.append(parameter)
          # Since rows are ordered, event data for a single event name is
          # grouped together and as such it's faster to insert new events at
          # the beginning so the loop on the next row finds the matching event
          # name immediately which saves cycles and because it's sortecd asc
          # and basically flipping the events as it processes them they will
          # come out in descending order.
          variables.insert(0, variable)
        else:
          existing_variable.parameters.append(parameter)

    return variables

  def get_first_party_variables(self, dataset: str, table: str) -> list[Variable]:
    """Look up and return the field names for use in feature/label selection.

    Args:
      dataset_name: The dataset where the first party table is located.

    Returns:
      A list of variables to be used for feature and label selection.
    """

    variables: list[Variable] = []

    exclude_type_list = [
        'DATE',
        'DATETIME',
        'TIME',
        'JSON',
        'RECORD'
    ]

    try:
      table = self.get_table(f'{dataset}.{table}')
    except NotFound:
      return variables

    for column in table.schema:
      if not column.field_type in exclude_type_list:
        parameter = Parameter('value', column.field_type)
        variable = Variable(column.name, Source.FIRST_PARTY, 0, [parameter])
        variables.append(variable)

    return variables

  def _quoted_list(self, list: list[str]):
    """Return a quoted list in string format.

    Args:
      list: The array/list of strings to convert.

    Returns:
      A quoted list of strings in string format (e.g. "value1","value2")
    """
    return '"' + str.join('","', list) + '"'
