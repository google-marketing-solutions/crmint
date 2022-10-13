"""Utilities for bigquery workers."""

import json
from typing import Any, Dict, Iterable

from google.cloud import bigquery
from google.cloud.bigquery.schema import SchemaField


def get_schema_field(field_config: Dict[str, Any]) -> SchemaField:
  """Converts a field config into a schema field instance.

  Args:
    field_config: Dictionary of the desired schema configuration.

  Returns:
    An instance of `google.cloud.bigquery.schema.SchemaField`.
  """
  sub_schema = [
      get_schema_field(f) for f in field_config.get('fields', [])
  ]
  return bigquery.schema.SchemaField(
      name=field_config['name'],
      field_type=field_config.get('type', 'STRING'),
      mode=field_config.get('mode', 'NULLABLE'),
      fields=sub_schema)


def parse_bigquery_json_schema(schema: str) -> Iterable[SchemaField]:
  """Parses a JSON encoded BigQuery schema.

  Args:
    schema: String containing the JSON encoded schema.

  Returns:
    A list of parsed field schemas representing the table schema.
  """
  decoded_schema = json.loads(schema)
  table_schema = [get_schema_field(f) for f in decoded_schema]
  return table_schema


def bytes_converter(total_bytes_processed: int) -> str:
  """Converts bytes processed output to different size equivalent.

  Args:
    total_bytes_processed: Integer of bytes processed for query.

  Returns:
    A conversion of bytes expressed in a different file size.
  """
  if total_bytes_processed / 1000 < 1000:
    kilobytes = round(total_bytes_processed / 1000, 2)
    return f'{kilobytes} KB'
  elif total_bytes_processed / (1000 * 1000) < 1000:
    megabytes = round(total_bytes_processed / (1000 * 1000), 2)
    return f'{megabytes} MB'
  elif total_bytes_processed / (1000 * 1000 * 1000) < 1000:
    gigabytes = round(total_bytes_processed / (1000 * 1000 * 1000), 2)
    return f'{gigabytes} GB'
  else:
    terabytes = round(total_bytes_processed / (1000 * 1000 * 1000 * 1000), 2)
    return f'{terabytes} TB'
