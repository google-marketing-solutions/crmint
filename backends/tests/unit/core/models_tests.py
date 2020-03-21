# Copyright 2018 Google Inc
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

from google.appengine.ext import testbed
from core import models

import os
import sys
sys.path.insert(0, os.getcwd())
from tests import utils


class TestPipeline(utils.ModelTestCase):

  def setUp(self):
    super(TestPipeline, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_taskqueue_stub()
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestPipeline, self).tearDown()
    self.testbed.deactivate()

  def test_create_pipeline_succeed(self):
    pipeline = models.Pipeline.create()
    obj = models.Pipeline.find(pipeline.id)
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

    self.assertEqual(len(pipeline.schedules.all()), 2)
    pipeline.assign_schedules(schedules_to_assign)
    self.assertEqual(len(pipeline.schedules.all()), 3)
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
    self.assertEqual(len(pipeline.params.all()), 2)
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
    self.assertEqual(len(pipeline.schedules.all()), 0)
    self.assertEqual(len(pipeline.params.all()), 0)
    pipeline.save_relations(relations)
    self.assertEqual(len(pipeline.schedules.all()), 1)
    self.assertEqual(len(pipeline.params.all()), 1)

  def test_is_blocked_if_run_on_schedule(self):
    pipeline = models.Pipeline.create(run_on_schedule=True)
    self.assertTrue(pipeline.is_blocked())

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
    p1 = models.Param.create(name='P1', type='string', value='foo')
    p2 = models.Param.create(name='P2', type='string', value='bar')
    p3 = models.Param.create(pipeline_id=pipeline.id, name='P2', type='string',
                             value='baz')
    p4 = models.Param.create(pipeline_id=pipeline.id, name='P3', type='string',
                             value='goo')
    p5 = models.Param.create(job_id=job.id, name='P3', type='string',
                             value='{% P1 %} {% P2 %} {% P3 %} zaz')
    success = pipeline.populate_params_runtime_values()
    self.assertEqual(success, True)
    self.assertEqual(p5.runtime_value, 'foo baz goo zaz')

class TestJob(utils.ModelTestCase):

  def setUp(self):
    super(TestJob, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJob, self).tearDown()
    self.testbed.deactivate()

  def test_job_succeeds_get_ready_with_pipeline_parameter(self):
    pipeline = models.Pipeline.create()
    models.Param.create(
        pipeline_id=pipeline.id,
        name='ABC',
        type='number',
        value='123')
    job1 = models.Job.create(pipeline_id=pipeline.id)
    models.Param.create(
        job_id=job1.id,
        name='field1',
        type='number',
        value='{% ABC %}')
    self.assertTrue(job1.get_ready())

  def test_job_succeeds_get_ready_with_global_parameter(self):
    models.Param.create(
        name='ABC',
        type='number',
        value='123')
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    models.Param.create(
        job_id=job1.id,
        name='field1',
        type='number',
        value='abc')  # initialize with a non-boolean value
    self.assertTrue(job1.get_ready())

  def test_task_succeeded_succeeds(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(
        pipeline_id=pipeline.id)
    self.assertEqual(job.status, models.Job.STATUS.IDLE)
    self.assertTrue(job.get_ready())
    self.assertEqual(job.status, models.Job.STATUS.WAITING)
    task = job.start()
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    job.task_succeeded(task.name)
    self.assertEqual(job.status, models.Job.STATUS.SUCCEEDED)

  def test_task_succeeded_fails_with_failed_task(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(
        pipeline_id=pipeline.id)
    self.assertTrue(job.get_ready())
    self.assertEqual(job.status, models.Job.STATUS.WAITING)
    task = job.start()
    self.assertIsNotNone(task)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    job.task_failed(task.name)
    self.assertEqual(job.status, models.Job.STATUS.FAILED)

  def test_save_relations(self):
    pipeline = models.Pipeline.create()
    job0 = models.Job.create(pipeline_id=pipeline.id)
    job1 = models.Job.create(pipeline_id=pipeline.id)
    start_conditions = [{
        'id': None,
        'preceding_job_id': job0.id,
        'condition': models.StartCondition.CONDITION.SUCCESS}
    ]
    params = [
        {'id': None, 'name': 'desc', 'label': 'Label', 'type': 'text',
         'value': 'Hello world!'}
    ]
    relations = {'start_conditions': start_conditions, 'params': params}
    self.assertEqual(len(job1.start_conditions), 0)
    self.assertEqual(len(job1.params.all()), 0)
    job1.save_relations(relations)
    self.assertEqual(len(job1.start_conditions), 1)
    self.assertEqual(len(job1.params.all()), 1)


class TestParam(utils.ModelTestCase):

  def test_job_id_and_pipeline_id_mutually_exclusive(self):
    # TODO(dulacp) implement this check
    pass


class TestParamSupportsType(utils.ModelTestCase):

  def _setup_parent_job(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    self.job = models.Job.create(name='job1', pipeline_id=pipeline.id)

class TestParamSupportsTypeBoolean(TestParamSupportsType):

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


class TestParamSupportsTypeString(TestParamSupportsType):

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


class TestParamSupportsTypeNumber(TestParamSupportsType):

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
    self.assertEqual(param.worker_value, 0)

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


class TestParamSupportsTypeStringList(TestParamSupportsType):

  def test_worker_value_succeeds_with_list_of_str(self):
    self._setup_parent_job()
    param = models.Param.create(job_id=self.job.id, name='p1',
                                type='string_list', value='foo\nbar\njohn')
    param.populate_runtime_value()
    self.assertIsInstance(param.worker_value, list)
    self.assertEqual(len(param.worker_value), 3)
    self.assertEqual(param.worker_value[0], 'foo')
    self.assertEqual(param.worker_value[1], 'bar')
    self.assertEqual(param.worker_value[2], 'john')


class TestParamSupportsTypeNumberList(TestParamSupportsType):

  def test_worker_value_succeeds_with_list_of_str(self):
    self._setup_parent_job()
    param = models.Param.create(job_id=self.job.id, name='p1',
                                type='number_list', value='1\n3\n2.8')
    param.populate_runtime_value()
    self.assertIsInstance(param.worker_value, list)
    self.assertEqual(len(param.worker_value), 3)
    self.assertEqual(param.worker_value[0], 1)
    self.assertEqual(param.worker_value[1], 3)
    self.assertEqual(param.worker_value[2], 2.8)


class TestParamRuntimeValues(utils.ModelTestCase):

  def test_global_param_runtime_value_is_populated_with_null(self):
    param = models.Param.create(name='p1', type='number', value='42')
    param.populate_runtime_value()
    self.assertEqual(param.runtime_value, None)

  def test_pipeline_param_runtime_value_is_populated_with_null(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    param = models.Param.create(pipeline_id=pipeline.id, name='p1',
                                type='number', value='42')
    param.populate_runtime_value()
    self.assertEqual(param.runtime_value, None)

  def test_job_param_runtime_value_is_populated_with_value(self):
    pipeline = models.Pipeline.create(name='pipeline1')
    job = models.Job.create(name='job1', pipeline_id=pipeline.id)
    param = models.Param.create(job_id=job.id, name='p1',
                                type='number', value='42')
    param.populate_runtime_value()
    self.assertEqual(param.runtime_value, '42')


class TestStage(utils.ModelTestCase):

  def test_assign_attributes(self):
    st = models.Stage.create()
    attrs = {'sid': '123'}
    self.assertNotEqual(st.sid, '123')
    st.assign_attributes(attrs)
    self.assertEqual(st.sid, '123')


class TestTaskEnqueued(utils.ModelTestCase):

  def test_count_is_zero(self):
    self.assertEqual(models.TaskEnqueued.count_in_namespace('xyz'), 0)

  def test_count_is_zero_in_another_namespace(self):
    models.TaskEnqueued.create(task_namespace='abc')
    self.assertEqual(models.TaskEnqueued.count_in_namespace('xyz'), 0)

  def test_count_is_not_zero_in_another_namespace(self):
    models.TaskEnqueued.create(task_namespace='xyz')
    models.TaskEnqueued.create(task_namespace='abc')
    self.assertEqual(models.TaskEnqueued.count_in_namespace('xyz'), 1)
