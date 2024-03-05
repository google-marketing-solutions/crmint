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
  """Represents a single variable (used for feature/label/etc selection)."""
  name: str
  source: str
  count: int
  parameters: list[Parameter]


class CustomClient(bigquery.Client):
  """BigQuery client wrapper that adds custom methods for easy access to necessary data."""

  def __init__(self, location: str) -> None:
    super().__init__(location=location)

  def get_analytics_variables(self,
                              project: str,
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

    event_exclude_list = """
      "user_engagement",
      "scroll",
      "session_start",
      "first_visit",
      "page_view"
    """

    key_exclude_list = """
      "debug_mode",
      "engagement_time_msec"
    """

    query = f"""
      WITH events AS (
        SELECT
          event_name AS name,
          event_params AS params
        FROM `{project}.{dataset}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN
          FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {start} DAY)) AND
          FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {end} DAY))
        AND event_name NOT IN ({event_exclude_list})
      ),
      top_events AS (
        SELECT
          name,
          COUNT(*) AS count
        FROM events
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 100
      )
      SELECT
        e.name,
        t.count,
        p.key AS parameter_key,
        STRING_AGG(
          DISTINCT
          CASE
            WHEN p.value.string_value IS NOT NULL THEN "string"
            WHEN p.value.int_value IS NOT NULL THEN "int"
            WHEN p.value.double_value IS NOT NULL THEN "double"
            WHEN p.value.float_value IS NOT NULL THEN "float"
          END
        ) AS parameter_value_type
      FROM events e,
      UNNEST(e.params) AS p
      JOIN top_events t ON e.name = t.name
      WHERE p.key NOT IN ({key_exclude_list})
      AND (
        p.value.string_value IS NOT NULL OR
        p.value.int_value IS NOT NULL OR
        p.value.double_value IS NOT NULL OR
        p.value.float_value IS NOT NULL
      )
      GROUP BY 1,2,3
      ORDER BY
        count DESC,
        name ASC,
        parameter_key ASC;
    """
    try:
      job = self.query(query=query)
      events = list(job.result())
    except NotFound:
      return variables

    variable: Variable = None
    lastIndex: int = len(events) - 1

    for index, event in enumerate(events):
      if index == 0 or variable.name != event.name:
        variable = Variable(event.name, Source.GOOGLE_ANALYTICS, event.count, [])

      variable.parameters.append(
        Parameter(event.parameter_key, event.parameter_value_type))

      if index == lastIndex or variable.name != events[index + 1].name:
        variables.append(variable)

    return variables

  def get_first_party_variables(self, project: str, dataset: str, table: str) -> list[Variable]:
    """Look up and return the field names for use in feature/label selection.

    Args:
      dataset_name: The dataset where the first party table is located.

    Returns:
      A list of variables to be used for feature and label selection.
    """

    variables: list[Variable] = []

    try:
      table = self.get_table(f'{project}.{dataset}.{table}')
    except NotFound:
      return variables

    for column in table.schema:
      if column.field_type not in ['JSON', 'RECORD']:
        parameter = Parameter('value', column.field_type)
        variable = Variable(column.name, Source.FIRST_PARTY, 0, [parameter])
        variables.append(variable)

    return variables