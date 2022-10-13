"""Tests for bq_utils."""

from absl.testing import absltest
from absl.testing import parameterized
from google.cloud import bigquery

from jobs.workers.bigquery import bq_utils


class BigqueryUtilsTest(parameterized.TestCase):

  def test_get_schema_field_with_float_required(self):
    field_config = {'name': 'foo', 'type': 'FLOAT64', 'mode': 'REQUIRED'}
    schema = bq_utils.get_schema_field(field_config)
    self.assertEqual(schema,
                     bigquery.SchemaField('foo', 'FLOAT64', mode='REQUIRED'))

  def test_get_schema_field_with_string_nullable(self):
    field_config = {'name': 'foo', 'type': 'STRING', 'mode': 'NULLABLE'}
    schema = bq_utils.get_schema_field(field_config)
    self.assertEqual(schema,
                     bigquery.SchemaField('foo', 'STRING', mode='NULLABLE'))

  def test_get_schema_field_with_with_sub_fields(self):
    field_config = {
        'name': 'foo',
        'type': 'STRING',
        'mode': 'REQUIRED',
        'fields': [
            {'name': 'bar1', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
            {'name': 'bar2', 'type': 'STRING', 'mode': 'NULLABLE'},
        ],
    }
    schema = bq_utils.get_schema_field(field_config)
    self.assertEqual(
        schema,
        bigquery.SchemaField('foo', 'STRING', mode='REQUIRED', fields=[
            bigquery.SchemaField('bar1', 'FLOAT64', mode='NULLABLE'),
            bigquery.SchemaField('bar2', 'STRING', mode='NULLABLE'),
        ]))

  def test_parsing_json_schema(self):
    schema_json_encoded = """
    [
        {"name": "foo", "type": "STRING", "mode": "NULLABLE"},
        {"name": "bar", "type": "STRING", "mode": "NULLABLE"}
    ]
    """
    schema = bq_utils.parse_bigquery_json_schema(schema_json_encoded)
    self.assertEqual(
        schema,
        [
            bigquery.SchemaField('foo', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('bar', 'STRING', mode='NULLABLE'),
        ])

  def test_bytes_converter(self):
    processed_units = bq_utils.bytes_converter(10000)
    self.assertEqual(processed_units, '10.0 KB')
    processed_units = bq_utils.bytes_converter(10000000)
    self.assertEqual(processed_units, '10.0 MB')
    processed_units = bq_utils.bytes_converter(10000000000)
    self.assertEqual(processed_units, '10.0 GB')
    processed_units = bq_utils.bytes_converter(10000000000000)
    self.assertEqual(processed_units, '10.0 TB')


if __name__ == '__main__':
  absltest.main()
