import os
import json

from datetime import date
from random import randint
from enum import Enum
from uuid import uuid4 as uuid
from jinja2 import Template, StrictUndefined
from controller.models import MlModel


class TemplateFile(Enum):
  TRAINING_PIPELINE = 'training_pipeline.json'
  PREDICTIVE_PIPELINE = 'predictive_pipeline.json'
  TRAINING_BQML = 'training_bqml.sql'
  PREDICTIVE_BQML = 'predictive_bqml.sql'
  GA4_REQUEST = 'ga4_request.json'
  OUTPUT = 'output.sql'


class Encoding(Enum):
  NONE = 'none'
  JSON = 'json'


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


# TODO: Leverage StrEnum once available in a later version (3.11) of python.
class ParamType(Enum):
  SQL = 'sql'
  TEXT = 'text'
  STRING = 'string'
  BOOLEAN = 'boolean'
  NUMBER = 'number'

  def __str__(self) -> str:
    return str(self.value)


# TODO: Leverage StrEnum once available in a later version (3.11) of python.
class Worker(Enum):
  BQ_SCRIPT_EXECUTOR = 'BQScriptExecutor'
  BQ_TO_MEASUREMENT_PROTOCOL_GA4 = 'BQToMeasurementProtocolGA4'
  BQ_TO_GOOGLE_ADS = 'BQToGoogleAds'

  def __str__(self) -> str:
    return str(self.value)


class UniqueId(str, Enum):
  USER_ID = 'USER_ID'
  CLIENT_ID = 'CLIENT_ID'


class Timespan():
  TRAINING: str = 'training'
  PREDICTIVE: str = 'predictive'

  training: int
  predictive: int
  random_training_set: list[int]
  random_predictive_set: list[int]

  def __init__(self) -> None:
    self.random_training_set = []
    self.random_predictive_set = []

  def generate_random_sets(self):
    """
    Generate a random training and predictive set to be used in the event standard date ranges are not sufficient.
    A random set (the size of the training timespan) of numbers between 0 and the total number of months in the timespan
    is created and the remaining months (those not selected for the training set) are used for the predictive set.
    """
    MAX = self.training + self.predictive

    self.random_training_set = self._generate_random_set(size=self.training, max=MAX)
    self.random_predictive_set = [n for n in range(MAX + 1) if n not in self.random_training_set]

  def _generate_random_set(self, size: int, max: int) -> list[int]:
    FIRST_MONTH = self.training + self.predictive
    LAST_MONTH = 0

    set = []
    while True:
      n = randint(0, max)
      if n not in set:
        set.append(n)

        # since the first and last months in the timespan are partial then select both if one is selected.
        if n == FIRST_MONTH:
          set.append(LAST_MONTH)
          size += 1
        elif n == LAST_MONTH:
          set.append(FIRST_MONTH)
          size += 1

        if len(set) == size:
          return set


class Destination(str, Enum):
  GOOGLE_ANALYTICS_CUSTOM_EVENT = 'GOOGLE_ANALYTICS_CUSTOM_EVENT',
  GOOGLE_ADS_CONVERSION_EVENT = 'GOOGLE_ADS_CONVERSION_EVENT'


class Compiler():
  """Used to build out pipeline configurations based on a series of templates in the templates directory."""
  project_id: str
  ga4_dataset: str
  ga4_measurement_id: str
  ga4_api_secret: str
  ml_model: MlModel

  def __init__(self, project_id: str, ga4_dataset: str, ga4_measurement_id: str, ga4_api_secret: str, ml_model: MlModel) -> None:
    self.project_id = project_id
    self.ga4_dataset = ga4_dataset
    self.ga4_measurement_id = ga4_measurement_id
    self.ga4_api_secret = ga4_api_secret
    self.ml_model = ml_model

  def build_training_pipeline(self) -> dict:
    """
    Builds the training pipeline configuration including the model SQL.

    Returns:
      A pipeline configuration for creating and training the model provided to the compiler.
    """
    pipeline_configuration = self._compile_template(TemplateFile.TRAINING_PIPELINE)
    return json.loads(pipeline_configuration)

  def build_predictive_pipeline(self) -> dict:
    """
    Builds the predictive pipeline configuration including the model SQL.

    Returns:
      A pipeline configuration for predicting values and uploading the results for the model provided to the compiler.
    """
    pipeline_configuration = self._compile_template(TemplateFile.PREDICTIVE_PIPELINE)
    return json.loads(pipeline_configuration)

  def _compile_template(self, templateFile: TemplateFile, encoding: Encoding = Encoding.NONE) -> str:
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
        'is_regression': self._is_regression(self.ml_model.type),
        'is_classification': self._is_classification(self.ml_model.type),
      },
      'uses_first_party_data': self.ml_model.uses_first_party_data,
      'unique_id': self._get_unique_id(self.ml_model.unique_id),
      'hyper_parameters': self.ml_model.hyper_parameters,
      'timespan': self._get_timespan(self.ml_model.timespans, 'month'),
      'label': self.ml_model.label,
      'features': self.ml_model.features,
      'skew_factor': self.ml_model.skew_factor,
      'destination': self.ml_model.destination
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
      'uuid': uuid
    }

    template = self._get_template(templateFile)
    rendered = template.render(**functions, **variables)
    if encoding == Encoding.JSON:
      return self._json_encode(rendered)
    else:
      return rendered

  def _get_template(self, templateFile: TemplateFile) -> Template:
    """Pulls appropriate template text from file."""
    options = {
      'comment_start_string': '--',
      'comment_end_string': '\n',
      'trim_blocks': True,
      'lstrip_blocks': True,
      'newline_sequence': '\n'
    }
    with open(self._absolute_path('templates/' + templateFile.value), 'r') as file:
      return Template(file.read(), **options, undefined=StrictUndefined)

  def _get_timespan(self, timespans: list) -> Timespan:
    """Returns the appropriate timespan (both training and predictive) with random sets built-in if needed."""

    ts = Timespan()

    for timespan in timespans:
      if timespan.name == Timespan.TRAINING:
        ts.training = timespan.value
      elif timespan.name == Timespan.PREDICTIVE:
        ts.predictive = timespan.value

    ts.generate_random_sets()
    return ts

  def _get_unique_id(self, type: UniqueId) -> str:
    """Get the actual unique identifier column name based on unique id type."""
    if type == UniqueId.USER_ID:
      return 'user_id'
    if type == UniqueId.CLIENT_ID:
      return 'user_pseudo_id'

  def _json_encode(self, text: str) -> str:
    """JSON encode a string of text provided without including double-quote wrapper."""
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

  def _is_regression(self, type: str) -> bool:
    """Checks whether or not the model is a regression type model."""
    return type in RegressionType._member_names_

  def _is_classification(self, type: str) -> bool:
    """Checks whether or not the model is a classification type model."""
    return type in ClassificationType._member_names_

  def _safe_day(self) -> str:
    """Returns the current day if safe to schedule and otherwise returns 28."""
    day = date.today().day
    return f'{day}' if day < 28 else '28'

  def _quarterly_months(self) -> str:
    """Returns the months of the year that occur quarterly (every 3 months)
      from the current month."""
    currentMonth = date.today().month
    months = ''
    for month in range(currentMonth, currentMonth + 11, 3):
      months += f'{month % 12 if month < 12 else month},'
    return months.removesuffix(',')

  def _absolute_path(self, file: str) -> str:
    """Returns the absolute path of the file assuming the file provided
      is in the current directory."""
    running_dir = os.getcwd()
    current_dir_relative = os.path.dirname(__file__)
    current_dir_full = os.path.join(running_dir, current_dir_relative)
    current_dir_absolute = os.path.realpath(current_dir_full)
    return os.path.join(current_dir_absolute, file)

