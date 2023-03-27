from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from enum import Enum
from datetime import date, timedelta

# Data Classes
class Parameter:
  """Model for a variable parameter."""

  key: str
  value_type: str

  def __init__(self, key: str, value_type: str) -> None:
    self.key = key
    self.value_type = value_type.lower()

class Variable:
  """Model for a single variable (used for feature/label selection)."""

  name: str
  source: str
  count: int
  parameters: list[Parameter]

  def __init__(self, name: str, source: str, count: int = 0) -> None:
    self.name = name
    self.source = source
    self.count = count
    self.parameters = []

class Source(Enum):
  GOOGLE_ANALYTICS = 'GOOGLE_ANALYTICS'
  FIRST_PARTY = 'FIRST_PARTY'

  def __str__(self) -> str:
    return str(self.value)

  def __eq__(self, other) -> bool:
    return other == str(self.value)


# BigQuery Client Wrapper
class Client(bigquery.Client):
  """BigQuery client wrapper that adds custom methods for easy access to necessary data."""

  def __init__(self, location: str) -> None:
    super().__init__(location=location)

  def get_analytics_variables(self, dataset_name: str) -> list[Variable]:
    """Get approximate counts, keys, and value_types for all GA4 events that happened in the last year."""

    variables: list[Variable] = []

    suffix = (date.today() - timedelta(days=7)).strftime('%Y%m%d')
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
      WHERE params.key NOT IN (
        'debug_mode', 'ga_session_id', 'ga_session_number', 'transaction_id'
      )
      GROUP BY 1,2,3
      HAVING parameter_value_type IS NOT NULL
      ORDER BY
        count ASC, # reversed to speed up data transformation step
        name ASC,
        parameter_key ASC;
    """
    job = self.query(query=query)
    rows = job.result()

    for row in rows:
      existing_variable = next((v for v in variables if v.name == row.name), None)
      parameter = Parameter(row.parameter_key, row.parameter_value_type)

      if not existing_variable:
        variable = Variable(row.name, Source.GOOGLE_ANALYTICS, row.count)
        variable.parameters.append(parameter)
        # since rows are ordered, event data for a single event name is grouped
        # together and as such it's faster to insert new events at the beginning
        # so the loop on the next row finds the matching event name immediately
        # which saves cycles and because it's sortecd asc and basically flipping
        # the events as it processes them they will come out in descending order.
        variables.insert(0, variable)
      else:
        existing_variable.parameters.append(parameter)

    return variables

  def get_first_party_variables(self, dataset_name: str) -> list[Variable]:
    """Look up and return the column/field names and their types for use in feature/label selection."""

    variables: list[Variable] = []

    if not self.table_exists(dataset_name, 'first_party'):
      return variables

    table = self.get_table(f'{dataset_name}.first_party')

    for column in table.schema:
      variable = Variable(column.name, Source.FIRST_PARTY)
      variable.parameters.append(Parameter('value', column.field_type))
      variables.append(variable)

    return variables

  def table_exists(self, dataset_name: str, table_name: str) -> bool:
    """Returns whether or not a table exists in this project under the provided dataset."""
    try:
      self.get_table(f'{dataset_name}.{table_name}')
      return True
    except NotFound:
      return False