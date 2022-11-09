"""Tests for controller.models."""

import textwrap

from absl.testing import absltest
import freezegun
import jinja2

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

  @freezegun.freeze_time('2022-05-15T00:00:00')
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

  @freezegun.freeze_time('2022-05-15T00:00:00')
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


if __name__ == '__main__':
  absltest.main()
