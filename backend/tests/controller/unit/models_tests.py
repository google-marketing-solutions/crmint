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


"""Tests for controller.models."""

import textwrap
from typing import Any, Union

from absl.testing import absltest
from absl.testing import parameterized
from freezegun import freeze_time
import jinja2

from controller import extensions
from controller import models
from tests import controller_utils


class TestParamSupportsTypeBase(controller_utils.ModelTestCase):

  def _setup_parent_job(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    self.job = models.Job.create(name='job1', pipeline_id=pipeline.id)


class TestParamSupportsTypeBoolean(TestParamSupportsTypeBase):

  def test_worker_value_succeeds_true(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='boolean', value='1')
    param.populate_runtime_value()
    self.assertEqual(param.worker_value, True)

  def test_worker_value_succeeds_false(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='boolean', value='0')
    param.populate_runtime_value()
    self.assertEqual(param.worker_value, False)

  def test_worker_value_fails_random_string(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='boolean', value='abc')
    param.populate_runtime_value()
    self.assertEqual(param.worker_value, False)

  def test_api_value_succeeds_true(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='boolean', value='1')
    self.assertEqual(param.api_value, True)

  def test_api_value_succeeds_false(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='boolean', value='0')
    self.assertEqual(param.api_value, False)


class TestParamSupportsTypeString(TestParamSupportsTypeBase):

  def test_worker_value_succeeds_with_regular_string(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='string', value='hello world!')
    param.populate_runtime_value()
    self.assertIsInstance(param.worker_value, str)
    self.assertEqual(param.worker_value, 'hello world!')

  def test_api_value_succeeds_with_string(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='string', value='john here')
    self.assertEqual(param.api_value, 'john here')


class TestParamSupportsTypeNumber(TestParamSupportsTypeBase):

  def test_worker_value_succeeds_with_integer(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='number', value='3')
    param.populate_runtime_value()
    self.assertIsInstance(param.worker_value, int)
    self.assertEqual(param.worker_value, 3)

  def test_worker_value_succeeds_with_float(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='number', value='5.1')
    param.populate_runtime_value()
    self.assertIsInstance(param.worker_value, float)
    self.assertEqual(param.worker_value, 5.1)

  def test_worker_value_fails_with_random_string(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='number', value='abc')
    param.populate_runtime_value()
    with self.assertRaisesRegex(ValueError, 'could not convert string'):
      _ = param.worker_value

  def test_api_value_succeeds_with_integer(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='number', value='3')
    self.assertEqual(param.api_value, '3')

  def test_api_value_succeeds_with_float(self):
    self._setup_parent_job()
    param = models.Param.create(
        job_id=self.job.id, name='p1', type='number', value='5.1')
    self.assertEqual(param.api_value, '5.1')


class TestParamSupportsTypeStringList(TestParamSupportsTypeBase):

  def test_worker_value_succeeds_with_list_of_str(self):
    self._setup_parent_job()
    param = models.Param.create(job_id=self.job.id, name='p1',
                                type='string_list', value='foo\nbar\njohn')
    param.populate_runtime_value()
    self.assertIsInstance(param.worker_value, list)
    self.assertLen(param.worker_value, 3)
    self.assertEqual(param.worker_value[0], 'foo')
    self.assertEqual(param.worker_value[1], 'bar')
    self.assertEqual(param.worker_value[2], 'john')


class TestParamSupportsTypeNumberList(TestParamSupportsTypeBase):

  def test_worker_value_succeeds_with_list_of_str(self):
    self._setup_parent_job()
    param = models.Param.create(job_id=self.job.id, name='p1',
                                type='number_list', value='1\n3\n2.8')
    param.populate_runtime_value()
    self.assertIsInstance(param.worker_value, list)
    self.assertLen(param.worker_value, 3)
    self.assertEqual(param.worker_value[0], 1)
    self.assertEqual(param.worker_value[1], 3)
    self.assertEqual(param.worker_value[2], 2.8)


class TestParamRuntimeValues(controller_utils.ModelTestCase):

  def test_global_param_runtime_value_is_populated_with_null(self):
    param = models.Param.create(name='p1', type='number', value='42')
    param.populate_runtime_value()
    self.assertIsNone(param.runtime_value)

  def test_pipeline_param_runtime_value_is_populated_with_null(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    param = models.Param.create(pipeline_id=pipeline.id, name='p1',
                                type='number', value='42')
    param.populate_runtime_value()
    self.assertIsNone(param.runtime_value)

  def test_job_param_runtime_value_is_populated_with_value(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(job_id=job.id, name='p1',
                                type='number', value='42')
    param.populate_runtime_value()
    self.assertEqual(param.runtime_value, '42')

  def test_job_param_runtime_value_can_render_old_variable_syntax(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(job_id=job.id, name='p1',
                                type='string', value='{% VAR_FOO %}')
    param.populate_runtime_value(context={'VAR_FOO': 'BAR'})
    self.assertEqual(param.runtime_value, 'BAR')

  def test_job_param_runtime_value_can_render_legacy_variable_syntax(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(job_id=job.id, name='p1',
                                type='string', value='foo %(var_foo).')
    param.populate_runtime_value(context={'var_foo': 'bar'})
    self.assertEqual(param.runtime_value, 'foo bar.')

  def test_job_param_runtime_value_can_render_new_jinja2_variable_syntax(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(job_id=job.id, name='p1',
                                type='string', value='{{ foo }}')
    param.populate_runtime_value(context={'foo': 'bar'})
    self.assertEqual(param.runtime_value, 'bar')

  def test_job_param_runtime_value_failed_on_unknown_variable(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(job_id=job.id, name='p1',
                                type='string', value='{{ foo }}')
    with self.assertRaises(jinja2.TemplateError):
      param.populate_runtime_value(context={'bar': 'abc'})

  @freeze_time('2022-05-15T00:00:00')
  def test_job_param_runtime_value_can_render_inline_function_today(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(
        job_id=job.id,
        name='p1',
        type='string',
        value='{{ today("%Y %m %d") }}')
    param.populate_runtime_value(context={'foo': 'bar'})
    self.assertEqual(param.runtime_value, '2022 05 15')

  @freeze_time('2022-05-15T00:00:00')
  def test_job_param_runtime_value_can_render_inline_function_days_ago(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(
        job_id=job.id,
        name='p1',
        type='string',
        value='{{ days_ago(3, "%Y-%m-%d") }}')
    param.populate_runtime_value(context={'foo': 'bar'})
    self.assertEqual(param.runtime_value, '2022-05-12')

  def test_job_param_runtime_value_can_render_forloops(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(
        job_id=job.id,
        name='p1',
        type='string',
        value=textwrap.dedent("""\
            {% for val in values -%}
              v: {{ val }}
            {% endfor %}
            """))
    param.populate_runtime_value(context={'values': range(3)})
    self.assertEqual(
        param.runtime_value,
        textwrap.dedent("""\
            v: 0
            v: 1
            v: 2
            """))


class TestPipeline(controller_utils.ModelTestCase):

  def test_create_pipeline_succeed(self):
    pipeline = models.Pipeline.create()
    obj = models.Pipeline.find(pipeline.id)
    self.assertLen(models.Pipeline.all(), 1)
    self.assertEqual(obj.id, pipeline.id)

  def test_assign_schedules_update_or_create_or_delete_relation(self):
    pipeline = models.Pipeline.create()
    sc1 = models.Schedule.create(pipeline_id=pipeline.id, cron='OLD')
    sc2 = models.Schedule.create(pipeline_id=pipeline.id, cron='NEW')

    # Update 1, Delete 1 and Create 2
    schedules_to_assign = [
        {'id': sc2.id, 'cron': 'UPDATED'},
        {'id': None, 'cron': 'NEW1'},
        {'id': None, 'cron': 'NEW2'},
    ]

    self.assertLen(models.Pipeline.all(), 1)
    self.assertCountEqual(
        pipeline.schedules,
        [sc1, sc2]
    )
    pipeline.assign_schedules(schedules_to_assign)
    self.assertLen(pipeline.schedules, 3)
    self.assertEqual(pipeline.schedules[0].id, sc2.id)
    self.assertEqual(pipeline.schedules[0].cron, 'UPDATED')
    self.assertEqual(pipeline.schedules[1].cron, 'NEW1')
    self.assertEqual(pipeline.schedules[2].cron, 'NEW2')

  def test_assign_params(self):
    pipeline = models.Pipeline.create()
    p1 = models.Param.create(
        id=7,
        pipeline_id=pipeline.id,
        name='checkbox0',
        type='boolean')
    params = [
        {'id': p1.id, 'name': 'checkbox1', 'label': 'CheckBox',
         'type': 'boolean', 'value': '0'},
        {'id': None, 'name': 'desc', 'label': 'Text', 'type': 'text',
         'value': 'Hello world!'},
    ]
    pipeline.assign_params(params)
    self.assertLen(pipeline.params, 2)
    self.assertEqual(pipeline.params[0].name, 'checkbox1')
    self.assertEqual(pipeline.params[1].name, 'desc')

  def test_assign_attributes(self):
    pipeline = models.Pipeline.create()
    attrs = {'schedules': [], 'jobs': [], 'params': [], 'name': 'John Lenon'}
    pipeline.assign_attributes(attrs)
    self.assertEqual(pipeline.name, 'John Lenon')

  def test_run_on_schedule_enabled(self):
    pipeline = models.Pipeline.create()
    attrs = {'run_on_schedule': 'True'}
    pipeline.assign_attributes(attrs)
    self.assertTrue(pipeline.run_on_schedule)

  def test_run_on_schedule_disabled(self):
    pipeline = models.Pipeline.create()
    attrs = {'run_on_schedule': 'NoMore or any other string'}
    pipeline.assign_attributes(attrs)
    self.assertFalse(pipeline.run_on_schedule)

  def test_save_relations(self):
    pipeline = models.Pipeline.create()
    schedules = [
        {'id': None, 'cron': 'NEW1'}
    ]
    params = [
        {'id': None, 'name': 'desc', 'label': 'Description', 'type': 'text',
         'value': 'Hello world!'}
    ]
    relations = {'schedules': schedules, 'params': params}
    self.assertEmpty(pipeline.schedules)
    self.assertEmpty(pipeline.params)
    pipeline.save_relations(relations)
    self.assertLen(pipeline.schedules, 1)
    self.assertLen(pipeline.params, 1)

  def test_is_blocked_if_run_on_schedule(self):
    pipeline = models.Pipeline.create(run_on_schedule=True)
    self.assertTrue(pipeline.is_blocked())

  def test_fails_get_ready_if_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    self.assertEqual(pipeline.get_ready(),
                     models.PipelineReadyStatus.ALREADY_RUNNING)

  def test_is_blocked_if_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    self.assertTrue(pipeline.is_blocked())

  def test_is_not_blocked_if_succeeded(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.SUCCEEDED)
    self.assertFalse(pipeline.is_blocked())

  def test_is_not_blocked_if_failed(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.FAILED)
    self.assertFalse(pipeline.is_blocked())

  def test_params_runtime_values_are_populated_successfully(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    _ = models.Param.create(name='P1', type='string', value='foo')
    _ = models.Param.create(name='P2', type='string', value='bar')
    _ = models.Param.create(pipeline_id=pipeline.id, name='P2', type='string',
                            value='baz')
    _ = models.Param.create(pipeline_id=pipeline.id, name='P3', type='string',
                            value='goo')
    p5 = models.Param.create(job_id=job.id, name='P3', type='string',
                             value='{% P1 %} {% P2 %} {% P3 %} zaz')
    success = pipeline.populate_params_runtime_values()
    self.assertEqual(success, True)
    self.assertEqual(p5.runtime_value, 'foo baz goo zaz')

  def test_has_no_jobs(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    self.assertFalse(pipeline.has_jobs)

  def test_has_jobs(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    _ = models.Job.create(name='job1', pipeline_id=pipeline.id)
    self.assertTrue(pipeline.has_jobs)


class TestTaskEnqueued(controller_utils.ModelTestCase):

  def test_count_is_zero(self):
    self.assertEqual(models.TaskEnqueued.count_in_namespace('xyz'), 0)

  def test_count_is_zero_in_another_namespace(self):
    models.TaskEnqueued.create(task_namespace='abc')
    self.assertEqual(models.TaskEnqueued.count_in_namespace('xyz'), 0)

  def test_count_is_not_zero_in_another_namespace(self):
    models.TaskEnqueued.create(task_namespace='xyz')
    models.TaskEnqueued.create(task_namespace='abc')
    self.assertEqual(models.TaskEnqueued.count_in_namespace('xyz'), 1)


class TestMlModel(controller_utils.ModelTestCase):

  def setUp(self):
    setup = super().setUp()
    self.ml_model = models.MlModel.create(name='Test Model',
                                          type='LOGISTIC_REG',
                                          unique_id='CLIENT_ID',
                                          destination='GOOGLE_ANALYTICS_CUSTOM_EVENT')
    return setup

  def test_ml_model_create(self):
    self.assertLen(models.MlModel.all(), 1)
    self.assertAttributesSaved({
      'name': 'Test Model',
      'type': 'LOGISTIC_REG',
      'unique_id': 'CLIENT_ID',
      'destination': 'GOOGLE_ANALYTICS_CUSTOM_EVENT'
    })

  def test_assign_attributes(self):
    attributes = {
      'name': 'Attribute Assigned',
      'type': 'BOOSTED_TREE_REGRESSOR',
      'unique_id': 'USER_ID',
      'uses_first_party_data': True,
      'class_imbalance': 7,
      'destination': 'GOOGLE_ADS_CONVERSION_EVENT'
    }
    self.ml_model.assign_attributes(attributes)
    self.assertAttributesSaved(attributes)

  @parameterized.named_parameters(
      ('create', {'name': 'CR-NAME', 'location': 'CR-LOC'}),
      ('update', {'name': 'UP-NAME', 'location': 'UP-LOC'}))
  def test_save_relations_bigquery_dataset(self, dataset):
    self.assertIsNone(self.ml_model.bigquery_dataset)
    self.ml_model.save_relations({'bigquery_dataset': dataset})
    self.assertRelationSaved(models.MlModelBigQueryDataset, dataset)

  @parameterized.named_parameters(
      ('create', [{'name': 'click', 'source': 'FIRST_PARTY'}]),
      (
          'update',
          [
              {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
              {'name': 'subscribe', 'source': 'FIRST_PARTY'},
          ],
      ),
      ('delete', []))
  def test_save_relations_features(self, features):
    self.assertLen(self.ml_model.features, 0)
    self.ml_model.save_relations({'features': features})
    self.assertRelationSaved(models.MlModelFeature, features)

  @parameterized.named_parameters(
      (
          'create',
          {
              'name': 'CR-NAME',
              'source': 'FIRST_PARTY',
              'key': 'CR-KEY',
              'value_type': 'CR-VT',
              'average_value': 1234,
          },
      ),
      (
          'update',
          {
              'name': 'UP-NAME',
              'source': 'GOOGLE_ANALYTICS',
              'key': 'UP-KEY',
              'value_type': 'UP-VT',
          },
      ))
  def test_save_relations_label(self, label):
    self.assertIsNone(self.ml_model.label)
    self.ml_model.save_relations({'label': label})
    self.assertRelationSaved(models.MlModelLabel, label)

  @parameterized.named_parameters(
      ('create', [{'name': 'L1_REG', 'value': '1'}]),
      (
          'update',
          [{'name': 'L1_REG', 'value': '2'}, {'name': 'L2_REG', 'value': '1'}],
      ),
      ('delete', []))
  def test_save_relations_hyper_parameters(self, hyper_parameters):
    self.assertLen(self.ml_model.hyper_parameters, 0)
    self.ml_model.save_relations({'hyper_parameters': hyper_parameters})
    self.assertRelationSaved(models.MlModelHyperParameter, hyper_parameters)

  @parameterized.named_parameters(
      ('create', [{'name': 'training', 'value': 11, 'unit': 'month'}]),
      (
          'update',
          [
              {'name': 'training', 'value': 1, 'unit': 'year'},
              {'name': 'predictive', 'value': 1, 'unit': 'month'},
          ],
      ),
      ('delete', []))
  def test_save_relations_pipelines(self, expected_objects):
    self.assertLen(self.ml_model.pipelines, 0)

    self.ml_model.save_relations(
        {
            'pipelines': [{
                'name': 'Test Model - Training Pipeline',
                'params': [],
                'jobs': [{
                    'id': 'de5cf393-24b6-4fbd-8cd3-3563d47aeace',
                    'name': 'Test Model - Training Job',
                    'worker_class': 'BQScriptExecutor',
                    'hash_start_conditions': [],
                    'params': [
                        {'type': 'sql', 'name': 'script', 'value': ''},
                        {
                            'type': 'string',
                            'name': 'bq_dataset_location',
                            'value': 'US',
                        },
                    ],
                }],
                'schedules': [{'cron': '0 0 21 */3 0'}],
            }]
        }
    )

    pipeline = models.Pipeline.where(ml_model_id=self.ml_model.id).first()
    self.assertIsNotNone(pipeline)

    pipeline = models.Pipeline.where(ml_model_id=self.ml_model.id).first()
    self.assertIsNotNone(pipeline)
    self.assertEqual(pipeline.name, 'Test Model - Training Pipeline')
    self.assertLen(pipeline.jobs, 1)
    self.assertLen(pipeline.jobs[0].params, 2)
    self.assertLen(pipeline.schedules, 1)

  def test_destroy_removes_all_relations(self):
    self.ml_model.save_relations({
        'bigquery_dataset': {'name': 'CR-NAME', 'location': 'CR-LOC'},
        'hyper_parameters': [{'name': 'L1_REG', 'value': '1'}],
        'features': [
            {'name': 'click', 'source': 'GOOGLE_ANALYTICS'},
            {'name': 'subscribe', 'source': 'FIRST_PARTY'},
        ],
        'label': {
            'name': 'CR-NAME',
            'source': 'FIRST_PARTY',
            'key': 'CR-KEY',
            'value_type': 'CR-VT',
        },
        'pipelines': [{
            'name': 'Test Model - Training Pipeline',
            'params': [],
            'jobs': [{
                'id': 'de5cf393-24b6-4fbd-8cd3-3563d47aeace',
                'name': 'Test Model - Training Job',
                'worker_class': 'BQScriptExecutor',
                'hash_start_conditions': [],
                'params': [
                    {'type': 'sql', 'name': 'script', 'value': ''},
                    {
                        'type': 'string',
                        'name': 'bq_dataset_location',
                        'value': 'US',
                    },
                ],
            }],
            'schedules': [{'cron': '0 0 21 */3 0'}],
        }],
    })

    model_id = self.ml_model.id

    self.ml_model.destroy()

    self.assertIsNone(
        models.MlModelBigQueryDataset.where(ml_model_id=model_id).first()
    )
    self.assertIsNone(
        models.MlModelHyperParameter.where(ml_model_id=model_id).first()
    )
    self.assertIsNone(models.MlModelFeature.where(ml_model_id=model_id).first())
    self.assertIsNone(models.MlModelLabel.where(ml_model_id=model_id).first())
    self.assertIsNone(models.Pipeline.where(ml_model_id=model_id).first())

  def assertAttributesSaved(self, assertions: dict[str, Any]):
    """
    Custom assertion that checks the MlModel.

    Using find and ensures the assertions provided match what's saved.

    Args:
      assertions: Dictionary of assertions to validate
    """
    row = models.MlModel.find(self.ml_model.id)
    for key, value in assertions.items():
      self.assertEqual(getattr(row, key), value)

  def assertRelationSaved(
      self,
      model: extensions.db.Model,
      assertions: Union[dict[str, Any], list[Any]]):
    """Custom assertion that checks the saved model matches expectations."""
    if isinstance(assertions, dict):
      row = model.where(ml_model_id=self.ml_model.id).first()
      for key, value in assertions.items():
        self.assertEqual(getattr(row, key), value)
    elif isinstance(assertions, list):
      rows = model.where(ml_model_id=self.ml_model.id).all()
      self.assertLen(rows, len(assertions))
      if rows:
        assertions.sort(key=lambda c: c['name'])
        rows.sort(key=lambda c: c.name)
        for index, assertion in enumerate(assertions):
          row_dict = rows[index].__dict__
          self.assertDictEqual(row_dict, row_dict | assertion)


if __name__ == '__main__':
  absltest.main()
