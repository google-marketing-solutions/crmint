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
import mock

from core import models

from tests import utils


class TestPipeline(utils.ModelTestCase):

  def setUp(self):
    super(TestPipeline, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_taskqueue_stub()
    self.testbed.init_memcache_stub()
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
        {'id': p1.id, 'name': 'checkbox1', 'type': 'boolean', 'value': '0'},
        {'id': None, 'name': 'desc', 'type': 'text', 'value': 'Hello world!'},
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
        {'id': None, 'name': 'desc', 'type': 'text', 'value': 'Hello world!'}
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


class TestJob(utils.ModelTestCase):

  def setUp(self):
    super(TestJob, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJob, self).tearDown()
    self.testbed.deactivate()

  @mock.patch('core.cloud_logging.logger')
  def test_job_fails_get_ready_without_pipeline_param(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    models.Param.create(
        job_id=job1.id,
        name='field1',
        type='number',
        value='{% ABC %}')  # initialize with a non-number value
    self.assertFalse(job1.get_ready())

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
        pipeline_id=pipeline.id,
        enqueued_workers_count=1)
    self.assertEqual(job.get_status(), models.Job.STATUS.IDLE)
    self.assertTrue(job.get_ready())
    self.assertEqual(job.get_status(), models.Job.STATUS.WAITING)
    task = job.start()
    self.assertEqual(job.get_status(), models.Job.STATUS.RUNNING)
    job.set_status(models.Job.STATUS.SUCCEEDED)
    self.assertEqual(job.get_status(), models.Job.STATUS.SUCCEEDED)

  def test_task_succeeded_fails_with_failed_workers(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(
        pipeline_id=pipeline.id,
        enqueued_workers_count=2)
    self.assertTrue(job.get_ready())
    self.assertEqual(job.get_status(), models.Job.STATUS.WAITING)
    task = job.start()
    self.assertEqual(job.get_status(), models.Job.STATUS.RUNNING)
    job.set_status(models.Job.STATUS.FAILED)
    self.assertEqual(job.get_status(), models.Job.STATUS.FAILED)
    self.assertEqual(job.get_status(), models.Job.STATUS.FAILED)

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
        {'id': None, 'name': 'desc', 'type': 'text', 'value': 'Hello world!'}
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


class TestParamSupportsTypeBoolean(utils.ModelTestCase):

    def test_val_succeeds_true(self):
      param = models.Param.create(name='p1', type='boolean', value='1')
      self.assertEqual(param.val, True)

    def test_val_succeeds_false(self):
      param = models.Param.create(name='p1', type='boolean', value='0')
      self.assertEqual(param.val, False)

    def test_val_fails_random_string(self):
      param = models.Param.create(name='p1', type='boolean', value='abc')
      self.assertEqual(param.val, False)

    def test_api_val_succeeds_true(self):
      param = models.Param.create(name='p1', type='boolean', value='1')
      self.assertEqual(param.api_val, True)

    def test_api_val_succeeds_false(self):
      param = models.Param.create(name='p1', type='boolean', value='0')
      self.assertEqual(param.api_val, False)


class TestParamSupportsTypeString(utils.ModelTestCase):

    def test_val_succeeds_with_regular_string(self):
      param = models.Param.create(
          name='p1',
          type='string',
          value='hello world!')
      self.assertIsInstance(param.val, str)
      self.assertEqual(param.val, 'hello world!')

    def test_api_val_succeeds_with_string(self):
      param = models.Param.create(name='p1', type='string', value='john here')
      self.assertEqual(param.api_val, 'john here')


class TestParamSupportsTypeNumber(utils.ModelTestCase):

    def test_val_succeeds_integer(self):
      param = models.Param.create(name='p1', type='number', value='3')
      self.assertIsInstance(param.val, int)
      self.assertEqual(param.val, 3)

    def test_val_succeeds_float(self):
      param = models.Param.create(name='p1', type='number', value='5.1')
      self.assertIsInstance(param.val, float)
      self.assertEqual(param.val, 5.1)

    def test_val_fails_with_random_string(self):
      param = models.Param.create(name='p1', type='number', value='abc')
      self.assertEqual(param.val, 0)


class TestParamSupportsTypeStringList(utils.ModelTestCase):

    def test_val_succeeds_with_list_of_str(self):
      param = models.Param.create(
          name='p1',
          type='string_list',
          value='foo\nbar\njohn')
      self.assertIsInstance(param.val, list)
      self.assertEqual(len(param.val), 3)
      self.assertEqual(param.val[0], 'foo')
      self.assertEqual(param.val[1], 'bar')
      self.assertEqual(param.val[2], 'john')


class TestParamSupportsTypeNumberList(utils.ModelTestCase):

    def test_val_succeeds_with_list_of_str(self):
      param = models.Param.create(
          name='p1',
          type='number_list',
          value='1\n3\n2.8')
      self.assertIsInstance(param.val, list)
      self.assertEqual(len(param.val), 3)
      self.assertEqual(param.val[0], 1)
      self.assertEqual(param.val[1], 3)
      self.assertEqual(param.val[2], 2.8)


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
