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
import datetime
import enum
from typing import Callable, TypeVar

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from common import utils

T = TypeVar('T')


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


# TODO(dulacp): Leverage StrEnum once we upgrade Python to 3.11
class Source(enum.Enum):
  GOOGLE_ANALYTICS = 'GOOGLE_ANALYTICS'
  FIRST_PARTY = 'FIRST_PARTY'

  def __str__(self) -> str:
    return str(self.value)

  def __eq__(self, other) -> bool:
    return other == str(self.value)


class CustomClient(bigquery.Client):
  """BigQuery client wrapper that adds custom methods for easy access to necessary data."""

  def __init__(self, location: str) -> None:
    super().__init__(location=location)

  def get_analytics_variables(self, dataset_name: str) -> list[Variable]:
    """Get approximate counts for all GA4 events that happened in the last year.

    Args:
      dataset_name: The dataset where the GA4 events tables are located.

    Returns:
      A list of variables to be used for feature and label selection.
    """

    event_exclude_list = [
        'user_engagement', 'scroll', 'session_start', 'first_visit', 'page_view'
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
        'engagement_time_msec',
    ]

    variables: list[Variable] = []

    suffix = (
        datetime.date.today() - datetime.timedelta(days=7)
    ).strftime('%Y%m%d')
    if not self.table_exists(dataset_name, f'events_{suffix}'):
      return variables

    query = f"""
      WITH event AS (
        SELECT
          event.value AS name,
          event.count
        FROM (
          SELECT APPROX_TOP_COUNT(event_name, 100) AS event_counts
          FROM `{self.project}.{dataset_name}.events_*`
          WHERE _TABLE_SUFFIX BETWEEN
            FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)) AND
            FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH))
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
    job = self.query(query=query)
    events = job.result()

    def make_condition_func(event_name: str) -> Callable[[T], bool]:
      return lambda x: x.name == event_name

    for event in events:
      if event.name not in event_exclude_list:
        try:
          existing_variable = utils.first(
              variables, make_condition_func(event.name))
        except StopIteration:
          existing_variable = None
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

    exclude_list = ['user_id', 'user_pseudo_id', 'trigger_event_date']
    variables: list[Variable] = []

    if not self.table_exists(dataset_name, 'first_party'):
      return variables

    table = self.get_table(f'{dataset_name}.first_party')

    for column in table.schema:
      if column.name not in exclude_list:
        parameter = Parameter('value', column.field_type)
        variable = Variable(column.name, Source.FIRST_PARTY, 0, [parameter])
        variables.append(variable)

    return variables

  def table_exists(self, dataset_name: str, table_name: str) -> bool:
    """Returns whether or not a table exists in this project."""
    try:
      self.get_table(f'{dataset_name}.{table_name}')
      return True
    except NotFound:
      return False
