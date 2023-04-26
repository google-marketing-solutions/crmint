import os

from datetime import date
from enum import Enum
from uuid import uuid4 as uuid
from jinja2 import Template, StrictUndefined


class TemplateFile(Enum):
  TRAINING = 'training.sql'
  CONVERSION_VALUES = 'conversion_values.sql'
  PREDICTIVE = 'predictive.sql'
  GA4_REQUEST = 'ga4_request.json'
  OUTPUT = 'output.sql'


class RegressionType(Enum):
  BOOSTED_TREE_REGRESSOR = 'BOOSTED_TREE_REGRESSOR'
  DNN_REGRESSOR = 'DNN_REGRESSOR'
  RANDOM_FOREST_REGRESSOR = 'RANDOM_FOREST_REGRESSOR'
  LINEAR_REG = 'LINEAR_REG'


class ClassificationType(Enum):
  BOOSTED_TREE_CLASSIFIER = 'BOOSTED_TREE_CLASSIFIER'
  DNN_CLASSIFIER = 'DNN_CLASSIFIER'
  RANDOM_FOREST_CLASSIFIER = 'RANDOM_FOREST_CLASSIFIER'
  LOGISTIC_REG = 'LOGISTIC_REG'


class UniqueId(str, Enum):
  USER_ID = 'USER_ID'
  CLIENT_ID = 'CLIENT_ID'


class Timespan():
  TRAINING: str = 'training'
  PREDICTIVE: str = 'predictive'

  training: int
  predictive: int

  @property
  def training_start(self) -> int:
    return self.training + self.predictive

  @property
  def predictive_start(self) -> int:
    return self.predictive


def build_training_pipeline(ml_model, project_id: str, ga4_dataset: str) -> dict:
  """Builds the training pipeline configuration including the model SQL."""
  setup_job_id = uuid()
  pipeline = {
    'name': f'{ml_model.name} - Training',
    'params': [],
    'jobs': [{
      'id': setup_job_id,
      'name': f'{ml_model.name} - Training Setup',
      'worker_class': 'BQScriptExecutor',
      'hash_start_conditions': [],
      'params': [
        {
          'name': 'script',
          'type': 'sql',
          'value': _compile_template(ml_model, project_id, ga4_dataset, TemplateFile.TRAINING)
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

  if _is_classification(ml_model.type):
    pipeline['jobs'].append({
      'id': uuid(),
      'name': f'{ml_model.name} - Conversion Value Calculations',
      'worker_class': 'BQScriptExecutor',
      'hash_start_conditions': [{
        'preceding_job_id': setup_job_id,
        'condition': 'success'
      }],
      'params': [
        {
          'name': 'script',
          'type': 'sql',
          'value': _compile_template(ml_model, project_id, ga4_dataset, TemplateFile.CONVERSION_VALUES)
        },
        {
          'name': 'bq_dataset_location',
          'type': 'string',
          'value': ml_model.bigquery_dataset.location
        }
      ]
    })

  return pipeline

def build_predictive_pipeline(ml_model, project_id: str, ga4_dataset: str, ga4_measurement_id: str, ga4_api_secret: str) -> dict:
  setup_job_id = uuid()
  output_job_id = uuid()
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
            'value': _compile_template(ml_model, project_id, ga4_dataset, TemplateFile.PREDICTIVE)
          },
          {
            'name': 'bq_dataset_location',
            'type': 'string',
            'value': ml_model.bigquery_dataset.location
          }
        ]
      },
      {
        'id': output_job_id,
        'name': f'{ml_model.name} - Predictive Output',
        'hash_start_conditions': [{
          'preceding_job_id': setup_job_id,
          'condition': 'success'
        }],
        'worker_class': 'BQScriptExecutor',
        'params': [
          {
            'name': 'script',
            'type': 'sql',
            'value': _compile_template(ml_model, project_id, ga4_dataset, TemplateFile.OUTPUT),
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
          'preceding_job_id': output_job_id,
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
            'value': 'output'
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
            'value': _compile_template(ml_model, project_id, ga4_dataset, TemplateFile.GA4_REQUEST)
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

def _compile_template(ml_model, project_id: str, ga4_dataset: str, templateFile: TemplateFile) -> str:
  """Builds the BQML SQL using the base template and the provided data."""
  variables = {
    'project_id': project_id,
    'model_dataset': ml_model.bigquery_dataset.name,
    'ga4_dataset': ga4_dataset,
    'type': {
      'name': ml_model.type,
      'is_regression': _is_regression(ml_model.type),
      'is_classification': _is_classification(ml_model.type),
    },
    'uses_first_party_data': ml_model.uses_first_party_data,
    'unique_id': _get_unique_id(ml_model.unique_id),
    'hyper_parameters': ml_model.hyper_parameters,
    'timespan': _get_timespan(ml_model.timespans),
    'label': ml_model.label,
    'features': ml_model.features,
    'class_imbalance': ml_model.class_imbalance
  }

  functions = {
    'is_number': _is_number,
    'is_bool': _is_bool
  }

  template = _get_template(templateFile)
  return template.render(**functions, **variables)

def _get_template(templateFile: TemplateFile) -> Template:
  """Pulls appropriate template text from file."""
  options = {
    'comment_start_string': '--',
    'comment_end_string': '\n',
    'trim_blocks': True,
    'lstrip_blocks': True,
    'newline_sequence': '\n'
  }
  with open(_absolute_path('templates/' + templateFile.value), 'r') as file:
    return Template(file.read(), **options, undefined=StrictUndefined)

def _get_timespan(timespans: list) -> Timespan:
  """Returns the appropriate timespan (both training and predictive) pulled from the list provided."""

  ts = Timespan()

  for timespan in timespans:
    if timespan.name == Timespan.TRAINING:
      ts.training = timespan.value
    elif timespan.name == Timespan.PREDICTIVE:
      ts.predictive = timespan.value

  return ts

def _get_unique_id(type: UniqueId) -> str:
  """Get the actual unique identifier column name based on unique id type."""
  if type == UniqueId.USER_ID:
    return 'user_id'
  if type == UniqueId.CLIENT_ID:
    return 'user_pseudo_id'

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

def _is_regression(type: str) -> bool:
  """Checks whether or not the model is a regression type model."""
  return type in RegressionType._member_names_

def _is_classification(type: str) -> bool:
  """Checks whether or not the model is a classification type model."""
  return type in ClassificationType._member_names_

def _safe_day() -> str:
  """Returns the current day if safe to schedule and otherwise returns 28."""
  day = date.today().day
  return f'{day}' if day < 28 else '28'

def _quarterly_months() -> str:
  """Returns the months of the year that occur quarterly (every 3 months)
     from the current month."""
  currentMonth = date.today().month
  months = ''
  for month in range(currentMonth, currentMonth + 11, 3):
    months += f'{month % 12 if month < 12 else month},'
  return months.removesuffix(',')

def _absolute_path(file: str) -> str:
  """Returns the absolute path of the file assuming the file provided
     is in the current directory."""
  running_dir = os.getcwd()
  current_dir_relative = os.path.dirname(__file__)
  current_dir_full = os.path.join(running_dir, current_dir_relative)
  current_dir_absolute = os.path.realpath(current_dir_full)
  return os.path.join(current_dir_absolute, file)

