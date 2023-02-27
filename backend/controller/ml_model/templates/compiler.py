import re
import os

from datetime import date
from enum import Enum
from uuid import uuid4 as uuid
from typing import Union

class Template(Enum):
  TRAINING = 'training.sql'
  PREDICTIVE = 'predictive.sql'
  GA4_REQUEST = 'ga4_request.json'
  SCORES = 'scores.sql'

def build_training_pipeline(ml_model, project_id: str, ga4_dataset: str) -> dict:
  """Builds the training pipeline configuration including the model SQL."""
  return {
    'name': f'{ml_model.name} - Training',
    'params': [],
    'jobs': [{
      'id': uuid(),
      'name': f'{ml_model.name} - Training Setup',
      'worker_class': 'BQScriptExecutor',
      'hash_start_conditions': [],
      'params': [
        {
          'name': 'script',
          'type': 'sql',
          'value': _compile_sql_template(ml_model, project_id, ga4_dataset, Template.TRAINING)
        },
        {
          'name': 'bq_dataset_location',
          'type': 'string',
          'value': ml_model.bigquery_dataset.location
        }
      ]
    }],
    'schedules': [{
      'cron': f'0 0 {_safe_day()} {_quarterly_months()} *'
    }]
  }

def build_predictive_pipeline(ml_model, project_id: str, ga4_dataset: str, ga4_measurement_id: str, ga4_api_secret: str) -> dict:
  setup_job_id = uuid()
  scores_job_id = uuid()
  ga4_upload_job_id = uuid()

  return {
    'name': f'{ml_model.name} - Predictive',
    'params': [],
    'jobs': [
      {
        'id': setup_job_id,
        'name': f'{ml_model.name} - Predictive Setup',
        'hash_start_conditions': [],
        'worker_class': 'BQScriptExecutor',
        'params': [
          {
            'name': 'script',
            'type': 'sql',
            'value': _compile_sql_template(ml_model, project_id, ga4_dataset, Template.PREDICTIVE)
          },
          {
            'name': 'bq_dataset_location',
            'type': 'string',
            'value': ml_model.bigquery_dataset.location
          }
        ]
      },
      {
        'id': scores_job_id,
        'name': f'{ml_model.name} - Predictive Scores',
        'hash_start_conditions': [{
          'preceding_job_id': setup_job_id,
          'condition': 'success'
        }],
        'worker_class': 'BQScriptExecutor',
        'params': [
          {
            'name': 'script',
            'type': 'sql',
            'value': _compile_sql_template(ml_model, project_id, ga4_dataset, Template.SCORES),
          },
          {
            'name': 'bq_dataset_location',
            'type': 'string',
            'value': ml_model.bigquery_dataset.location
          }
        ]
      },
      {
        'id': ga4_upload_job_id,
        'name': f'{ml_model.name} - Predictive GA4 Upload',
        'hash_start_conditions': [{
          'preceding_job_id': scores_job_id,
          'condition': 'success'
        }],
        'worker_class': 'BQToMeasurementProtocolGA4',
        'params': [
          {
            'name': 'bq_project_id',
            'type': 'string',
            'value': project_id
          },
          {
            'name': 'bq_dataset_id',
            'type': 'string',
            'value': ml_model.bigquery_dataset.name
          },
          {
            'name': 'bq_dataset_location',
            'type': 'string',
            'value': ml_model.bigquery_dataset.location
          },
          {
            'name': 'bq_table_id',
            'type': 'string',
            'value': 'scores'
          },
          {
            'name': 'measurement_id',
            'type': 'string',
            'value': ga4_measurement_id
          },
          {
            'name': 'api_secret',
            'type': 'string',
            'value': ga4_api_secret
          },
          {
            'name': 'template',
            'type': 'text',
            'value': _get_template(Template.GA4_REQUEST)
          },
          {
            'name': 'mp_batch_size',
            'type': 'number',
            'value': '20'
          },
          {
            'name': 'debug',
            'type': 'boolean',
            'value': False
          }
        ]
      }
    ],
    'schedules': [{
      'cron': '0 0 * * *'
    }]
  }

def _compile_sql_template(ml_model, project_id: str, ga4_dataset: str, template: Template) -> str:
  """Builds the BQML SQL using the base template and the provided data."""
  variables = {
    '__PROJECT_ID__': project_id,
    '__ML_MODEL_TYPE__': ml_model.type,
    '__ML_MODEL_DATASET__': ml_model.bigquery_dataset.name,
    '__GA4_DATASET__': ga4_dataset,
    '__ML_MODEL_HYPER_PARAMTERS__': _compile_hyper_parameters(ml_model.hyper_parameters),
    '__ML_MODEL_TIMESPAN_MONTHS__': _get_timespan(ml_model.timespans, 'month', template),
    '__ML_MODEL_LABEL_NAME__': ml_model.label.name,
    '__ML_MODEL_LABEL_KEY__': ml_model.label.key,
    '__ML_MODEL_LABEL_VALUE_STATEMENT__': _compile_label_value_statement(ml_model.label.value_type),
    '__ML_MODEL_FEATURES__': _compile_features(ml_model.features),
    '__ML_MODEL_SKEW_FACTOR__': ml_model.skew_factor
  }

  sql = _get_template(template)
  sql = _remove_comments(sql)
  return _replace(variables, sql)

def _get_template(template: Template) -> str:
  """Pulls appropriate template text from file."""
  with open(_absolute_path(template.value), 'r') as file:
    return file.read()

def _replace(replacements: dict, template: str) -> str:
  """Uses the key for each of the replacements to find a string in the template
     and replaces that string with the value associated to that key."""
  compiled = template
  for needle, replacement in replacements.items():
    compiled = compiled.replace(needle, str(replacement))
  return compiled

def _remove_comments(sql: str) -> str:
  """Removes comments from the sql provided."""
  return re.sub(r'\-\-.*\n', '', str(sql))

def _compile_hyper_parameters(params: list) -> str:
  """Builds the SQL for the hyper parameters using the list provided."""
  compiled = ''
  suffix = ',\n  '
  for param in params:
    if _is_number(param.value):
      compiled += f'{param.name} = {param.value}'
    elif _is_bool(param.value):
      compiled += f'{param.name} = {param.value.upper()}'
    else:
      compiled += f'{param.name} = "{param.value}"'
    compiled += suffix
  return compiled.removesuffix(suffix)

def _compile_features(features: list) -> str:
  """Builds the SQL for the features using the list provided."""
  compiled = ''
  suffix = ',\n    '
  for feature in features:
    compiled += f'SUM(IF(name = "{feature.name}", 1, 0)) AS cnt_{feature.name}{suffix}'
  return compiled.removesuffix(suffix)

def _compile_label_value_statement(type: str) -> str:
  """Builds the SQL for the label value type based on the type provided."""
  if 'string' in type:
    return 'COALESCE(params.value.string_value, params.value.int_value) NOT IN ("", "0", 0, NULL)'
  else:
    return 'COALESCE(params.value.int_value, params.value.float_value, params.value.double_value) > 0'

def _get_timespan(timespans: list, unit: str, template: str) -> Union[int, None]:
  map = {
    Template.TRAINING: 'training',
    Template.PREDICTIVE: 'predictive'
  }

  if name := map.get(template, None):
    for timespan in timespans:
      if timespan.name == name and timespan.unit == unit:
        return timespan.value

  return None

def _is_number(value: str) -> bool:
  """Checks a string value to determine if it's a number."""
  try:
    float(value)
    return True
  except ValueError:
    return False

def _is_bool(value: str) -> bool:
  """Checks a string value to determine if it's a boolean."""
  return value.lower() in ['true', 'false']

def _safe_day() -> str:
  """Returns the current day if safe to schedule and otherwise returns 28."""
  day = date.today().day
  return f'{day}' if day < 28 else '28'

def _quarterly_months() -> str:
  """Returns the months of the year that occur quarterly (every 3 months) from the current month."""
  currentMonth = date.today().month
  months = ''
  for month in range(currentMonth, currentMonth + 11, 3):
    months += f'{month % 12 if month < 12 else month},'
  return months.removesuffix(',')

def _absolute_path(file: str) -> str:
  """Returns the absolute path of the file assuming the file provided is in the current directory."""
  running_dir = os.getcwd()
  current_dir_relative = os.path.dirname(__file__)
  current_dir_full = os.path.join(running_dir, current_dir_relative)
  current_dir_absolute = os.path.realpath(current_dir_full)
  return os.path.join(current_dir_absolute, file)

