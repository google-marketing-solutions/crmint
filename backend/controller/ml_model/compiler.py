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

"""MlModel template compiler."""

import datetime
import enum
import os
from typing import Any
import uuid

from jinja2 import StrictUndefined
from jinja2 import Template

from controller import models


class TemplateFile(enum.Enum):
  TRAINING = 'training.sql'
  CONVERSION_VALUES = 'conversion_values.sql'
  PREDICTIVE = 'predictive.sql'
  GA4_REQUEST = 'ga4_request.json'
  OUTPUT = 'output.sql'


class RegressionType(enum.Enum):
  BOOSTED_TREE_REGRESSOR = 'BOOSTED_TREE_REGRESSOR'
  DNN_REGRESSOR = 'DNN_REGRESSOR'
  RANDOM_FOREST_REGRESSOR = 'RANDOM_FOREST_REGRESSOR'
  LINEAR_REG = 'LINEAR_REG'


class ClassificationType(enum.Enum):
  BOOSTED_TREE_CLASSIFIER = 'BOOSTED_TREE_CLASSIFIER'
  DNN_CLASSIFIER = 'DNN_CLASSIFIER'
  RANDOM_FOREST_CLASSIFIER = 'RANDOM_FOREST_CLASSIFIER'
  LOGISTIC_REG = 'LOGISTIC_REG'


class UniqueId(str, enum.Enum):
  USER_ID = 'USER_ID'
  CLIENT_ID = 'CLIENT_ID'


class Timespan:
  """Encapsulates a timespan."""
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


def build_training_pipeline(obj,
                            project_id: str,
                            ga4_dataset: str) -> dict[str, Any]:
  """Builds the training pipeline configuration including the model SQL."""
  setup_job_id = uuid.uuid4()
  pipeline = {
      'name': f'{obj.name} - Training',
      'params': [],
      'jobs': [{
          'id': setup_job_id,
          'name': f'{obj.name} - Training Setup',
          'worker_class': 'BQScriptExecutor',
          'hash_start_conditions': [],
          'params': [
              {
                  'name': 'script',
                  'type': 'sql',
                  'value': _compile_template(obj,
                                             project_id,
                                             ga4_dataset,
                                             TemplateFile.TRAINING)
              },
              {
                  'name': 'bq_dataset_location',
                  'type': 'string',
                  'value': obj.bigquery_dataset.location
              }
          ]
      }],
      'schedules': [{
          'cron': f'0 0 {_safe_day()} {_quarterly_months()} *'
      }]
  }

  if _is_classification(obj.type):
    pipeline['jobs'].append({
        'id': uuid.uuid4(),
        'name': f'{obj.name} - Conversion Value Calculations',
        'worker_class': 'BQScriptExecutor',
        'hash_start_conditions': [{
            'preceding_job_id': setup_job_id,
            'condition': 'success'
        }],
        'params': [
            {
                'name': 'script',
                'type': 'sql',
                'value': _compile_template(obj,
                                           project_id,
                                           ga4_dataset,
                                           TemplateFile.CONVERSION_VALUES)
            },
            {
                'name': 'bq_dataset_location',
                'type': 'string',
                'value': obj.bigquery_dataset.location
            }
        ]
    })

  return pipeline


def build_predictive_pipeline(obj,
                              project_id: str,
                              ga4_dataset: str,
                              ga4_measurement_id: str,
                              ga4_api_secret: str) -> dict[str, Any]:
  setup_job_id = uuid.uuid4()
  output_job_id = uuid.uuid4()
  ga4_upload_job_id = uuid.uuid4()

  return {
      'name': f'{obj.name} - Predictive',
      'params': [],
      'jobs': [
          {
              'id': setup_job_id,
              'name': f'{obj.name} - Predictive Setup',
              'hash_start_conditions': [],
              'worker_class': 'BQScriptExecutor',
              'params': [
                  {
                      'name': 'script',
                      'type': 'sql',
                      'value': _compile_template(obj,
                                                 project_id,
                                                 ga4_dataset,
                                                 TemplateFile.PREDICTIVE)
                  },
                  {
                      'name': 'bq_dataset_location',
                      'type': 'string',
                      'value': obj.bigquery_dataset.location
                  }
              ]
          },
          {
              'id': output_job_id,
              'name': f'{obj.name} - Predictive Output',
              'hash_start_conditions': [{
                  'preceding_job_id': setup_job_id,
                  'condition': 'success'
              }],
              'worker_class': 'BQScriptExecutor',
              'params': [
                  {
                      'name': 'script',
                      'type': 'sql',
                      'value': _compile_template(obj,
                                                 project_id,
                                                 ga4_dataset,
                                                 TemplateFile.OUTPUT),
                  },
                  {
                      'name': 'bq_dataset_location',
                      'type': 'string',
                      'value': obj.bigquery_dataset.location
                  }
              ]
          },
          {
              'id': ga4_upload_job_id,
              'name': f'{obj.name} - Predictive GA4 Upload',
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
                      'value': obj.bigquery_dataset.name
                  },
                  {
                      'name': 'bq_dataset_location',
                      'type': 'string',
                      'value': obj.bigquery_dataset.location
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
                      'value': _compile_template(obj,
                                                 project_id,
                                                 ga4_dataset,
                                                 TemplateFile.GA4_REQUEST)
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
          'cron': '0 0 * * *',
      }]
  }


def _compile_template(obj,
                      project_id: str,
                      ga4_dataset: str,
                      template_file: TemplateFile) -> str:
  """Builds the BQML SQL using the base template and the provided data."""
  variables = {
      'project_id': project_id,
      'model_dataset': obj.bigquery_dataset.name,
      'ga4_dataset': ga4_dataset,
      'type': {
          'name': obj.type,
          'is_regression': _is_regression(obj.type),
          'is_classification': _is_classification(obj.type),
      },
      'uses_first_party_data': obj.uses_first_party_data,
      'unique_id': _get_unique_id(obj.unique_id),
      'hyper_parameters': obj.hyper_parameters,
      'timespan': _get_timespan(obj.timespans),
      'label': obj.label,
      'features': obj.features,
      'class_imbalance': obj.class_imbalance
  }

  functions = {
      'is_number': _is_number,
      'is_bool': _is_bool,
  }

  template = _get_template(template_file)
  return template.render(**functions, **variables)


def _get_template(template_file: TemplateFile) -> Template:
  """Pulls appropriate template text from file."""
  options = {
      'comment_start_string': '--',
      'comment_end_string': '\n',
      'trim_blocks': True,
      'lstrip_blocks': True,
      'newline_sequence': '\n'
  }
  with open(_absolute_path('templates/' + template_file.value), 'r') as file:
    return Template(file.read(), **options, undefined=StrictUndefined)


def _get_timespan(timespans: list[models.MlModelTimespan]) -> Timespan:
  """Returns the appropriate timespan pulled from the list provided."""
  ts = Timespan()
  for timespan in timespans:
    if timespan.name == Timespan.TRAINING:
      ts.training = timespan.value
    elif timespan.name == Timespan.PREDICTIVE:
      ts.predictive = timespan.value
  return ts


def _get_unique_id(field_type: UniqueId) -> str:
  """Get the actual unique identifier column name based on unique id type."""
  if field_type == UniqueId.USER_ID:
    return 'user_id'
  if field_type == UniqueId.CLIENT_ID:
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


def _is_regression(field_type: str) -> bool:
  """Checks whether or not the model is a regression type model."""
  return field_type in [x.value for x in RegressionType]


def _is_classification(field_type: str) -> bool:
  """Checks whether or not the model is a classification type model."""
  return field_type in [x.value for x in ClassificationType]


def _safe_day() -> str:
  """Returns the current day if safe to schedule and otherwise returns 28."""
  day = datetime.date.today().day
  return f'{day}' if day < 28 else '28'


def _quarterly_months() -> str:
  """Returns the months of the year that occur quarterly."""
  current_month = datetime.date.today().month
  months = ''
  for month in range(current_month, current_month + 11, 3):
    months += f'{month % 12 if month < 12 else month},'
  return months.removesuffix(',')


def _absolute_path(file: str) -> str:
  """Returns the absolute path of the file.

  Assuming the file provided is in the current directory.

  Args:
    file: relative path to a file.
  """
  running_dir = os.getcwd()
  current_dir_relative = os.path.dirname(__file__)
  current_dir_full = os.path.join(running_dir, current_dir_relative)
  current_dir_absolute = os.path.realpath(current_dir_full)
  return os.path.join(current_dir_absolute, file)
