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
from controller import shared
import time


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


class Source(shared.StrEnum):
  GOOGLE_ANALYTICS = 'GOOGLE_ANALYTICS'
  FIRST_PARTY = 'FIRST_PARTY'


class CustomClient(bigquery.Client):
  """BigQuery client wrapper that adds custom methods for easy access to necessary data."""

  def __init__(self, location: str) -> None:
    super().__init__(location=location)

  def get_analytics_variables(self,
                              dataset_name: str,
                              start_day: int,
                              end_day: int) -> list[Variable]:
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

    time.sleep(120)

    event_exclude_list = [
        'user_engagement',
        'scroll',
        'session_start',
        'first_visit',
        'page_view'
    ]

    key_exclude_list = [
        'debug_mode',
        'ga_session_id',
        'ga_session_number',
        'transaction_id',
        'page_location',
        'page_referrer',
        'session_engaged',
        'engaged_session_event',
        'content_group',
        'engagement_time_msec'
    ]

    query = f"""
      WITH event AS (
        SELECT
          event.value AS name,
          event.count
        FROM (
          SELECT APPROX_TOP_COUNT(event_name, 100) AS event_counts
          FROM `{self.project}.{dataset_name}.events_*`
          WHERE _TABLE_SUFFIX BETWEEN
            FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {start_day} DAY)) AND
            FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {end_day} DAY))
        ), UNNEST(event_counts) AS event
      )
      SELECT
        event.name AS name,
        event.count AS count,
        params.key AS parameter_key,
        STRING_AGG(
          DISTINCT
          CASE
            WHEN params.value.string_value IS NOT NULL THEN 'string'
            WHEN params.value.int_value IS NOT NULL THEN 'int'
            WHEN params.value.double_value IS NOT NULL THEN 'double'
            WHEN params.value.float_value IS NOT NULL THEN 'float'
            ELSE NULL
          END
        ) AS parameter_value_type
      FROM `{self.project}.{dataset_name}.events_*`,
            UNNEST(event_params) AS params
      JOIN event ON event.name = event_name
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
          if parameter.key not in key_exclude_list:
            variable.parameters.append(parameter)
          # Since rows are ordered, event data for a single event name is
          # grouped together and as such it's faster to insert new events at
          # the beginning so the loop on the next row finds the matching event
          # name immediately which saves cycles and because it's sortecd asc
          # and basically flipping the events as it processes them they will
          # come out in descending order.
          variables.insert(0, variable)
        elif parameter.key not in key_exclude_list:
          existing_variable.parameters.append(parameter)

    return variables

  def get_first_party_variables(self, dataset_name: str) -> list[Variable]:
    """Look up and return the field names for use in feature/label selection.

    Args:
      dataset_name: The dataset where the first party table is located.

    Returns:
      A list of variables to be used for feature and label selection.
    """

    variables: list[Variable] = []

    exclude_list = [
        'user_id',
        'user_pseudo_id',
        'trigger_event_date'
    ]

    exclude_type_list = [
        'DATE',
        'DATETIME',
        'TIME',
        'JSON',
        'RECORD'
    ]

    try:
      table = self.get_table(f'{dataset_name}.first_party')
    except NotFound:
      return variables

    for column in table.schema:
      excluded_column: bool = column.name in exclude_list
      excluded_field_type: bool = column.field_type in exclude_type_list
      if not excluded_column and not excluded_field_type:
        parameter = Parameter('value', column.field_type)
        variable = Variable(column.name, Source.FIRST_PARTY, 0, [parameter])
        variables.append(variable)

    return variables
