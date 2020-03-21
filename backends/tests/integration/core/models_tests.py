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

from google.appengine.api import taskqueue
from google.appengine.ext import testbed
import mock

from core import models

import os
import sys
sys.path.insert(0, os.getcwd())
from tests import utils


class TestPipelineWithJobs(utils.ModelTestCase):

  def setUp(self):
    super(TestPipelineWithJobs, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_taskqueue_stub()
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestPipelineWithJobs, self).tearDown()
    self.testbed.deactivate()

  def test_start_fails_without_jobs(self):
    pipeline = models.Pipeline.create()
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)

  def test_start_fails_if_already_running(self):
    pipeline = models.Pipeline.create()
    pipeline.status = models.Pipeline.STATUS.RUNNING
    pipeline.save()
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)

  def test_start_succeeds_with_one_job_idle(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.start()
    self.assertEqual(result, True)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)

  def test_start_fails_with_one_job_running(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job1.status = models.Job.STATUS.RUNNING
    job1.save()
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)

  def test_start_succeeds_with_one_job_succeeded(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job1.status = models.Job.STATUS.SUCCEEDED
    job1.save()
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.start()
    self.assertEqual(result, True)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)

  def test_start_succeeds_with_one_job_failed(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job1.status = models.Job.STATUS.FAILED
    job1.save()
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.start()
    self.assertEqual(result, True)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)

  @mock.patch('core.cloud_logging.logger')
  def test_start_fails_with_pipeline_not_getting_ready(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    models.Param.create(
        job_id=job1.id,
        name='field1',
        type='number',
        value='{% ABC %}')  # initialize with a non-boolean value
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)

  @mock.patch('core.cloud_logging.logger')
  def test_start_fails_with_one_job_not_getting_ready(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    pipeline = models.Pipeline.create()
    # initialize a job with a non-active status
    job1 = models.Job.create(pipeline_id=pipeline.id,
                             status=models.Job.STATUS.RUNNING)
    models.Param.create(job_id=job1.id, name='field1', type='number', value='3')
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)

  def test_stop_fails_if_not_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.IDLE)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.stop()
    self.assertEqual(result, False)

  def test_stop_succeeds_and_stop_all_jobs(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.RUNNING)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.RUNNING)
    self.assertEqual(len(pipeline.jobs.all()), 3)
    self.assertEqual(pipeline.jobs[0].status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(pipeline.jobs[1].status, models.Job.STATUS.RUNNING)
    self.assertEqual(pipeline.jobs[2].status, models.Job.STATUS.RUNNING)
    result = pipeline.stop()
    self.assertTrue(result)
    self.assertEqual(pipeline.jobs[0].status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(pipeline.jobs[1].status, models.Job.STATUS.FAILED)
    self.assertEqual(pipeline.jobs[2].status, models.Job.STATUS.FAILED)

  def test_stop_succeeds_if_all_jobs_succeeded(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    self.assertEqual(len(pipeline.jobs.all()), 3)
    result = pipeline.stop()
    self.assertTrue(result)
    self.assertEqual(pipeline.jobs[0].status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(pipeline.jobs[1].status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(pipeline.jobs[2].status, models.Job.STATUS.SUCCEEDED)

  def test_start_single_job_succeeds(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.IDLE)
    job1 = models.Job.create(pipeline_id=pipeline.id)
    result = pipeline.start_single_job(job1)
    self.assertTrue(result)
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)

  def test_start_single_job_fails_if_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(pipeline_id=pipeline.id)
    result = pipeline.start_single_job(job1)
    self.assertFalse(result)
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)

  def test_job_finished_succeeds(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    result = pipeline.job_finished()
    self.assertTrue(result)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.SUCCEEDED)

  def test_job_finished_fails_if_one_remains(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.RUNNING)
    result = pipeline.job_finished()
    self.assertFalse(result)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)

  def test_job_finished_fails_if_mix_succeeded_and_failed(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    job2 = models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.FAILED)
    models.StartCondition.create(job_id=job2.id, preceding_job_id=None)
    result = pipeline.job_finished()
    self.assertTrue(result)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.FAILED)

  def test_pipeline_success_with_failed_condition_fulfilled(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    job2 = models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.FAILED)
    job3 = models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=models.StartCondition.CONDITION.FAIL)
    result = pipeline.job_finished()
    self.assertTrue(result)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.SUCCEEDED)

  def test_successfully_cancel_tasks_on_failure_without_conditions(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)

    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)

    task1 = job1.start()
    self.assertIsNotNone(task1)
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job1._enqueued_task_count(), 1)

    task2 = job2.start()
    self.assertIsNotNone(task2)
    self.assertEqual(job2.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2._enqueued_task_count(), 1)

    job2.task_failed(task2.name)
    self.assertEqual(job2.status, models.Job.STATUS.FAILED)

    # It should trigger the end of the pipeline by itself
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(job1._enqueued_task_count(), 0)
    self.assertEqual(job2._enqueued_task_count(), 0)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.FAILED)


class TestPipelineDestroy(utils.ModelTestCase):

  def setUp(self):
    super(TestPipelineDestroy, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestPipelineDestroy, self).tearDown()
    self.testbed.deactivate()

  def test_destroy_succeeds(self):
    pipeline = models.Pipeline.create()
    pipeline.destroy()
    self.assertIsNone(models.Pipeline.find(pipeline.id))

  def test_destroy_deletes_all_schedules(self):
    pipeline = models.Pipeline.create()
    sc1 = models.Schedule.create(pipeline_id=pipeline.id)
    self.assertIsNotNone(models.Schedule.find(sc1.id))
    pipeline.destroy()
    self.assertIsNone(models.Schedule.find(sc1.id))

  def test_destroy_deletes_all_jobs(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, name='j1')
    self.assertIsNotNone(models.Job.find(job1.id))
    pipeline.destroy()
    self.assertIsNone(models.Job.find(job1.id))

  def test_destroy_deletes_all_params(self):
    pipeline = models.Pipeline.create()
    param1 = models.Param.create(
        pipeline_id=pipeline.id,
        name='p1',
        type='string')
    self.assertIsNotNone(models.Param.find(param1.id))
    pipeline.destroy()
    self.assertIsNone(models.Param.find(param1.id))


class TestPipelineImport(utils.ModelTestCase):

  def setUp(self):
    super(TestPipelineImport, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_taskqueue_stub()
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestPipelineImport, self).tearDown()
    self.testbed.deactivate()

  def test_import_data_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create()
    job2 = models.Job.create()
    data = {
        'params': [
            {'name': 'p1', 'label': 'P1', 'type': 'string', 'value': 'foo'},
            {'name': 'p2', 'label': 'P2', 'type': 'string', 'value': 'bar'},
        ],
        'schedules': [
            {'id': None, 'cron': 'NEW1'},
            {'id': None, 'cron': 'NEW2'},
        ],
        'jobs': [
            {'id': job1.id, 'name': 'j1', 'hash_start_conditions': []},
            {'id': job2.id, 'name': 'j2', 'hash_start_conditions': []},
        ]
    }
    pipeline.import_data(data)
    self.assertEqual(len(pipeline.params.all()), 2)
    self.assertEqual(pipeline.params[0].name, 'p1')
    self.assertEqual(pipeline.params[0].label, 'P1')
    self.assertEqual(pipeline.params[0].value, 'foo')
    self.assertEqual(pipeline.params[1].name, 'p2')
    self.assertEqual(pipeline.params[1].label, 'P2')
    self.assertEqual(pipeline.params[1].value, 'bar')
    self.assertEqual(len(pipeline.jobs.all()), 2)
    self.assertEqual(pipeline.jobs[0].name, 'j1')
    self.assertEqual(pipeline.jobs[1].name, 'j2')


class TestJobStartedStatus(utils.ModelTestCase):

  def setUp(self):
    super(TestJobStartedStatus, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJobStartedStatus, self).tearDown()
    self.testbed.deactivate()

  def test_succeeds_status_running(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(pipeline_id=pipeline.id)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job.status, models.Job.STATUS.WAITING)
    self.assertTrue(job.start())
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)


class TestJobDestroy(utils.ModelTestCase):

  def setUp(self):
    super(TestJobDestroy, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestJobDestroy, self).tearDown()
    self.testbed.deactivate()

  def test_destroy_succeeds(self):
    job = models.Job.create()
    job.destroy()
    self.assertIsNone(models.Job.find(job.id))

  def test_destroy_deletes_all_starting_conditions(self):
    job1 = models.Job.create()
    job2 = models.Job.create()
    sc1 = models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id)
    self.assertIsNotNone(models.StartCondition.find(sc1.id))
    job2.destroy()
    self.assertIsNone(models.StartCondition.find(sc1.id))

  def test_destroy_deletes_preceding_starting_conditions(self):
    job1 = models.Job.create()
    job2 = models.Job.create()
    sc1 = models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id)
    self.assertIsNotNone(models.StartCondition.find(sc1.id))
    job1.destroy()
    self.assertIsNone(models.StartCondition.find(sc1.id))

  def test_destroy_deletes_all_params(self):
    job = models.Job.create()
    param1 = models.Param.create(
        job_id=job.id,
        name='p1',
        type='string')
    self.assertIsNotNone(models.Param.find(param1.id))
    job.destroy()
    self.assertIsNone(models.Param.find(param1.id))


class TestStartConditionWithJobs(utils.ModelTestCase):

  def setUp(self):
    super(TestStartConditionWithJobs, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestStartConditionWithJobs, self).tearDown()
    self.testbed.deactivate()

  def test_value_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, name='job1')
    job2 = models.Job.create(pipeline_id=pipeline.id, name='job2')
    sc1 = models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    self.assertEqual(sc1.value, '%s,success' % job1.id)

  def test_preceding_job_name_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, name='job1')
    job2 = models.Job.create(pipeline_id=pipeline.id, name='job2')
    sc1 = models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    self.assertEqual(sc1.preceding_job_name, 'job1')


class TestJobStartConditions(utils.ModelTestCase):

  def setUp(self):
    super(TestJobStartConditions, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJobStartConditions, self).tearDown()
    self.testbed.deactivate()

  def test_create_start_conditions_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    job2 = models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    job3 = models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    arg_start_conditions = [
        {'preceding_job_id': job1.id, 'condition': models.StartCondition.CONDITION.SUCCESS},
        {'preceding_job_id': job2.id, 'condition': models.StartCondition.CONDITION.SUCCESS},
    ]
    job3.assign_start_conditions(arg_start_conditions)
    self.assertEqual(len(job3.start_conditions), 2)

  def test_update_start_conditions_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    job3 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=models.StartCondition.CONDITION.FAIL)
    arg_start_conditions = [
        {
        'preceding_job_id': job1.id,
        'condition': models.StartCondition.CONDITION.SUCCESS},
        {
        'preceding_job_id': job2.id,
        'condition': models.StartCondition.CONDITION.SUCCESS},
    ]
    self.assertEqual(len(job3.start_conditions), 1)
    self.assertEqual(job3.start_conditions[0].condition,
        models.StartCondition.CONDITION.FAIL)
    job3.assign_start_conditions(arg_start_conditions)
    self.assertEqual(len(job3.start_conditions), 2)
    self.assertEqual(job3.start_conditions[0].condition,
        models.StartCondition.CONDITION.SUCCESS)
    self.assertEqual(job3.start_conditions[1].condition,
        models.StartCondition.CONDITION.SUCCESS)

  def test_fails_if_running(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(pipeline_id=pipeline.id)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job.status, models.Job.STATUS.WAITING)
    task1 = job.start()
    self.assertIsNotNone(task1)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    task2 = job.start()
    self.assertIsNone(task2)

  def test_succeeds_if_waiting_without_start_conditions(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(pipeline_id=pipeline.id)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job.status, models.Job.STATUS.WAITING)
    task = job.start()
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    self.assertIsNotNone(task)

  def test_succeeds_with_start_condition_fulfill_success_with_succeeded(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='success')
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    job1.task_succeeded(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(job2.status, models.Job.STATUS.RUNNING)

  def test_fails_with_start_condition_unfulfill_success_with_failed(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    job1.task_failed(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(job2.status, models.Job.STATUS.FAILED)

  def test_succeeds_with_start_condition_fulfill_fail_with_failed(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.FAIL)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    job1.task_failed(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(job2.status, models.Job.STATUS.RUNNING)
    self.assertNotEqual(pipeline.status, models.Pipeline.STATUS.FAILED)

  def test_fails_with_start_condition_unfulfill_fail_with_succeeded(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='fail')
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    job1.task_succeeded(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(job2.status, models.Job.STATUS.FAILED)

  def test_succeeds_with_start_condition_fulfill_whatever_with_failed(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.WHATEVER)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    job1.task_failed(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(job2.status, models.Job.STATUS.RUNNING)

  def test_succeeds_with_start_condition_fulfill_whatever_with_succeeded(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.WHATEVER)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    job1.task_succeeded(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(job2.status, models.Job.STATUS.RUNNING)

  def test_fails_with_start_condition_unfulfill_whatever_with_running(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.WHATEVER)
    self.assertTrue(pipeline.get_ready())
    task1 = job1.start()
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    task2 = job2.start()
    self.assertIsNone(task2)
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)


class TestJobStopConditions(utils.ModelTestCase):

  def setUp(self):
    super(TestJobStopConditions, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJobStopConditions, self).tearDown()
    self.testbed.deactivate()

  def test_stop_fails_with_idle(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)
    result = job1.stop()
    self.assertFalse(result)
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)

  def test_stop_reset_to_idle(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    result = job1.stop()
    self.assertTrue(result)
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)

  def test_stop_succeeds_with_running(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    self.assertTrue(pipeline.get_ready())
    task1 = job1.start()
    self.assertIsNotNone(task1)
    self.assertTrue(job1.stop())
    self.assertEqual(job1.status, models.Job.STATUS.STOPPING)

  def test_stop_succeeds_with_outdated_tasks(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    self.assertTrue(pipeline.get_ready())
    task1 = job1.start()
    self.assertIsNotNone(task1)
    taskqueue.Queue().delete_tasks([taskqueue.Task(name=task1.name)])
    self.assertTrue(job1.stop())
    self.assertEqual(job1.status, models.Job.STATUS.STOPPING)


class TestJobStartWithDependentJobs(utils.ModelTestCase):

  def setUp(self):
    super(TestJobStartWithDependentJobs, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJobStartWithDependentJobs, self).tearDown()
    self.testbed.deactivate()

  def test_start_fails_with_dependent_jobs_and_expecting_success(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    job3 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    self.assertEqual(job3.status, models.Job.STATUS.WAITING)
    task = job1.start()
    self.assertIsNotNone(task)
    job1.task_failed(task.name)
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(job2.status, models.Job.STATUS.FAILED)
    self.assertEqual(job3.status, models.Job.STATUS.FAILED)

  def test_start_fails_with_dependent_jobs_and_expecting_fail(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    job3 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.FAIL)
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    self.assertEqual(job3.status, models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertIsNotNone(task1)
    job1.task_succeeded(task1.name)
    task2 = job2.start()
    self.assertIsNone(task2)
    self.assertEqual(job2.status, models.Job.STATUS.FAILED)
    self.assertEqual(job3.status, models.Job.STATUS.FAILED)

  def test_dependent_job_starts_after_multiple_workers_finish_with_fail(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    job3 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.FAIL)
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job1.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    self.assertEqual(job3.status, models.Job.STATUS.WAITING)
    task1 = job1.start()
    task2 = job1.enqueue(job1.worker_class, {})
    self.assertIsNotNone(task1)
    job1.task_succeeded(task1.name)
    job1.task_failed(task2.name)
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    task3 = job2.start()
    self.assertIsNone(task3)
    self.assertEqual(job2.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job3.status, models.Job.STATUS.WAITING)


class TestJobStartingMultipleTasks(utils.ModelTestCase):

  def setUp(self):
    super(TestJobStartingMultipleTasks, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJobStartingMultipleTasks, self).tearDown()
    self.testbed.deactivate()

  def test_succeeds_completing_tasks_in_series(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(pipeline_id=pipeline.id)
    worker_params = dict([(p.name, p.val) for p in job.params])
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job.status, models.Job.STATUS.WAITING)
    task1 = job.start()
    self.assertIsNotNone(task1)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    task2 = job.enqueue(job.worker_class, worker_params)
    self.assertIsNotNone(task2)
    job.task_succeeded(task1.name)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    job.task_succeeded(task2.name)
    self.assertEqual(job.status, models.Job.STATUS.SUCCEEDED)

  def test_pipeline_fails_second_task_succeeded_fail_start_condition_fail(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job2 = models.Job.create(pipeline_id=pipeline.id)
    job3 = models.Job.create(pipeline_id=pipeline.id)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    pipeline.get_ready()
    task1 = job1.start()
    job1.task_failed(task1.name)
    self.assertTrue(job1.status, models.Job.STATUS.FAILED)
    self.assertTrue(job2.status, models.Job.STATUS.STOPPING)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.FAILED)

  def test_succeeds_completing_tasks_in_parallel(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(pipeline_id=pipeline.id)
    worker_params = dict([(p.name, p.val) for p in job.params])
    self.assertTrue(pipeline.get_ready())
    self.assertEqual(job.status, models.Job.STATUS.WAITING)
    task1 = job.start()
    self.assertIsNotNone(task1)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    task2 = job.enqueue(job.worker_class, worker_params)
    task3 = job.enqueue(job.worker_class, worker_params)
    self.assertIsNotNone(task2)
    self.assertIsNotNone(task3)
    job.task_succeeded(task1.name)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    job.task_succeeded(task3.name)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    job.task_succeeded(task2.name)
    self.assertEqual(job.status, models.Job.STATUS.SUCCEEDED)
