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
import os
import json
import enum
import uuid
import jinja2

from typing import Any
from controller import shared
from controller import models


class TemplateFile(shared.StrEnum):
  TRAINING_PIPELINE = 'training_pipeline.json'
  PREDICTIVE_PIPELINE = 'predictive_pipeline.json'
  TRAINING_BQML = 'training_bqml.sql'
  PREDICTIVE_BQML = 'predictive_bqml.sql'
  CONVERSION_VALUES_BQML = 'conversion_values_bqml.sql'
  GOOGLE_ANALYTICS_MP_EVENT = 'google_analytics_mp_event.json'
  GOOGLE_ADS_OFFLINE_CONVERSION = 'google_ads_offline_conversion.json'
  OUTPUT = 'output.sql'


class Encoding(enum.Enum):
  NONE = enum.auto()
  JSON = enum.auto()


class ModelTypes:
  REGRESSION: list[str] = [
    'BOOSTED_TREE_REGRESSOR',
    'DNN_REGRESSOR',
    'RANDOM_FOREST_REGRESSOR',
    'LINEAR_REG'
  ]
  CLASSIFICATION: list[str] = [
    'BOOSTED_TREE_CLASSIFIER',
    'DNN_CLASSIFIER',
    'RANDOM_FOREST_CLASSIFIER',
    'LOGISTIC_REG'
  ]


class ParamType(shared.StrEnum):
  SQL = 'sql'
  TEXT = 'text'
  STRING = 'string'
  BOOLEAN = 'boolean'
  NUMBER = 'number'


class Worker(shared.StrEnum):
  BQ_SCRIPT_EXECUTOR = 'BQScriptExecutor'
  BQ_TO_MEASUREMENT_PROTOCOL_GA4 = 'BQToMeasurementProtocolGA4'
  BQ_TO_GOOGLE_ADS_OFFLINE_CONVERSION = 'BQToAdsOfflineClickConversion'


class UniqueId(shared.StrEnum):
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
    return self.training + self.predictive + 1

  @property
  def predictive_start(self) -> int:
    return self.predictive + 1


class Destination(shared.StrEnum):
  GOOGLE_ANALYTICS_MP_EVENT = 'GOOGLE_ANALYTICS_MP_EVENT'
  GOOGLE_ADS_OFFLINE_CONVERSION = 'GOOGLE_ADS_OFFLINE_CONVERSION'


class Compiler():
  """
  Used to build out pipeline configurations based on a series of
  templates in the templates directory.
  """
  project_id: str
  ga4_dataset: str
  ga4_measurement_id: str
  ga4_api_secret: str
  ml_model: models.MlModel

  def __init__(self,
               project_id: str,
               ga4_dataset: str,
               ga4_measurement_id: str,
               ga4_api_secret: str,
               ml_model: models.MlModel) -> None:
    self.project_id = project_id
    self.ga4_dataset = ga4_dataset
    self.ga4_measurement_id = ga4_measurement_id
    self.ga4_api_secret = ga4_api_secret
    self.ml_model = ml_model

  def build_training_pipeline(self) -> dict[str, Any]:
    """
    Builds the training pipeline configuration including the model SQL.

    Returns:
      A pipeline configuration for creating and training the model
      provided to the compiler.
    """
    pipeline_configuration = self._compile_template(TemplateFile.TRAINING_PIPELINE)
    return json.loads(pipeline_configuration)

  def build_predictive_pipeline(self) -> dict[str, Any]:
    """
    Builds the predictive pipeline configuration including the model SQL.

    Returns:
      A pipeline configuration for predicting values and uploading the
      results for the model provided to the compiler.
    """
    pipeline_configuration = self._compile_template(TemplateFile.PREDICTIVE_PIPELINE)
    return json.loads(pipeline_configuration)

  def _compile_template(self,
                        templateFile: TemplateFile,
                        encoding: Encoding = Encoding.NONE) -> str:
    """Uses the template and data provided to render the result."""
    variables = {
      'name': self.ml_model.name,
      'project_id': self.project_id,
      'model_dataset': self.ml_model.bigquery_dataset.name,
      'ga4_dataset': self.ga4_dataset,
      'ga4_measurement_id': self.ga4_measurement_id,
      'ga4_api_secret': self.ga4_api_secret,
      'dataset_location': self.ml_model.bigquery_dataset.location,
      'type': {
        'name': self.ml_model.type,
        'is_regression': self.ml_model.type in ModelTypes.REGRESSION,
        'is_classification': self.ml_model.type in ModelTypes.CLASSIFICATION,
      },
      'uses_first_party_data': self.ml_model.uses_first_party_data,
      'unique_id': self._get_unique_id(self.ml_model.unique_id),
      'hyper_parameters': self.ml_model.hyper_parameters,
      'timespan': self._get_timespan(self.ml_model.timespans),
      'label': self.ml_model.label,
      'features': self.ml_model.features,
      'class_imbalance': self.ml_model.class_imbalance,
      'output_config': self.ml_model.output_config
    }

    constants = {
      'Worker': Worker,
      'ParamType': ParamType,
      'Destination': Destination,
      'TemplateFile': TemplateFile,
      'Encoding': Encoding
    }

    for key, value in constants.items():
      variables[key] = value

    functions = {
      'compile_template': self._compile_template,
      'is_number': self._is_number,
      'is_bool': self._is_bool,
      'safe_day': self._safe_day,
      'quarterly_months': self._quarterly_months,
      'uuid': uuid.uuid4
    }

    template = self._get_template(templateFile)
    rendered = template.render(**functions, **variables)
    if encoding == Encoding.JSON:
      return self._json_encode(rendered)
    else:
      return rendered

  def _get_template(self, templateFile: TemplateFile) -> jinja2.Template:
    """Pulls appropriate template text from file."""
    options = {
      'comment_start_string': '--',
      'comment_end_string': '\n',
      'trim_blocks': True,
      'lstrip_blocks': True,
      'newline_sequence': '\n'
    }
    with open(self._absolute_path('templates/' + templateFile), 'r') as file:
      return jinja2.Template(file.read(), **options, undefined=jinja2.StrictUndefined)

  def _get_timespan(self, timespans: list) -> Timespan:
    """
    Returns the appropriate timespan (both training and predictive)
    with random sets built-in if needed.
    """

    ts = Timespan()

    for timespan in timespans:
      if timespan.name == Timespan.TRAINING:
        ts.training = timespan.value
      elif timespan.name == Timespan.PREDICTIVE:
        ts.predictive = timespan.value

    return ts

  def _get_unique_id(self, type: UniqueId) -> str:
    """Get the actual unique identifier column name based on unique id type."""
    if type == UniqueId.USER_ID:
      return 'user_id'
    if type == UniqueId.CLIENT_ID:
      return 'user_pseudo_id'

  def _json_encode(self, text: str) -> str:
    """
    JSON encode a string of text provided without including
    double-quote wrapper.
    """
    return json.dumps(text).removeprefix('"').removesuffix('"')

  def _is_number(self, value: str) -> bool:
    """Checks a string value to determine if it's a number."""
    try:
      float(value)
      return True
    except ValueError:
      return False

  def _is_bool(self, value: str) -> bool:
    """Checks a string value to determine if it's a boolean."""
    return value.lower() in ['true', 'false']

  def _safe_day(self) -> str:
    """Returns the current day if safe to schedule and otherwise returns 28."""
    day = datetime.date.today().day
    return f'{day}' if day < 28 else '28'

  def _quarterly_months(self) -> str:
    """Returns the months of the year that occur quarterly (every 3 months)
      from the current month."""
    currentMonth = datetime.date.today().month
    months = ''
    for month in range(currentMonth, currentMonth + 11, 3):
      months += f'{month % 12 if month < 12 else month},'
    return months.removesuffix(',')

  def _absolute_path(self, file: str) -> str:
    """
    Returns the absolute path of the file assuming the file provided
    is in the current directory.
    """
    running_dir = os.getcwd()
    current_dir_relative = os.path.dirname(__file__)
    current_dir_full = os.path.join(running_dir, current_dir_relative)
    current_dir_absolute = os.path.realpath(current_dir_full)
    return os.path.join(current_dir_absolute, file)

