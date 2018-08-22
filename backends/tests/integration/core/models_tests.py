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


class TestPipelineWithJobs(utils.ModelTestCase):

  def setUp(self):
    super(TestPipelineWithJobs, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_taskqueue_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()

  def tearDown(self):
    super(TestPipelineWithJobs, self).tearDown()
    self.testbed.deactivate()

  def test_start_fails_without_jobs(self):
    pipeline = models.Pipeline.create()
    self.assertEqual(pipeline.status, 'idle')
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, 'idle')

  def test_start_fails_if_already_running(self):
    pipeline = models.Pipeline.create()
    pipeline.status = 'running'
    pipeline.save()
    self.assertEqual(pipeline.status, 'running')
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, 'running')

  def test_start_succeeds_with_one_job_idle(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    self.assertEqual(pipeline.status, 'idle')
    result = pipeline.start()
    self.assertEqual(result, True)
    self.assertEqual(pipeline.status, 'running')

  def test_start_fails_with_one_job_running(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job1.status = 'running'
    job1.save()
    self.assertEqual(pipeline.status, 'idle')
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, 'idle')

  def test_start_succeeds_with_one_job_succeeded(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job1.status = 'succeeded'
    job1.save()
    self.assertEqual(pipeline.status, 'idle')
    result = pipeline.start()
    self.assertEqual(result, True)
    self.assertEqual(pipeline.status, 'running')

  def test_start_succeeds_with_one_job_failed(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    job1.status = 'failed'
    job1.save()
    self.assertEqual(pipeline.status, 'idle')
    result = pipeline.start()
    self.assertEqual(result, True)
    self.assertEqual(pipeline.status, 'running')

  @mock.patch('core.logging.logger')
  def test_start_fails_with_one_job_not_getting_ready(self, patched_logger):
    patched_logger.log_struct.__name__ = 'foo'
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    models.Param.create(
        job_id=job1.id,
        name='field1',
        type='number',
        value='{% ABC %}')  # initialize with a non-boolean value
    self.assertEqual(pipeline.status, 'idle')
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, 'idle')

  def test_stop_fails_if_not_running(self):
    pipeline = models.Pipeline.create(status='idle')
    self.assertEqual(pipeline.status, 'idle')
    result = pipeline.stop()
    self.assertEqual(result, False)

  def test_stop_succeeds_and_stop_all_jobs(self):
    pipeline = models.Pipeline.create(status='running')
    models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    models.Job.create(pipeline_id=pipeline.id, status='running')
    models.Job.create(pipeline_id=pipeline.id, status='running')
    self.assertEqual(len(pipeline.jobs.all()), 3)
    self.assertEqual(pipeline.jobs[0].status, 'succeeded')
    self.assertEqual(pipeline.jobs[1].status, 'running')
    self.assertEqual(pipeline.jobs[2].status, 'running')
    result = pipeline.stop()
    self.assertTrue(result)
    self.assertEqual(pipeline.jobs[0].status, 'succeeded')
    self.assertEqual(pipeline.jobs[1].status, 'stopping')
    self.assertEqual(pipeline.jobs[2].status, 'stopping')

  def test_stop_succeeds_if_all_jobs_succeeded(self):
    pipeline = models.Pipeline.create(status='running')
    models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    self.assertEqual(len(pipeline.jobs.all()), 3)
    result = pipeline.stop()
    self.assertTrue(result)
    self.assertEqual(pipeline.jobs[0].status, 'succeeded')
    self.assertEqual(pipeline.jobs[1].status, 'succeeded')
    self.assertEqual(pipeline.jobs[2].status, 'succeeded')

  def test_start_single_job_succeeds(self):
    pipeline = models.Pipeline.create(status='idle')
    job1 = models.Job.create(pipeline_id=pipeline.id)
    result = pipeline.start_single_job(job1)
    self.assertTrue(result)
    self.assertEqual(job1.get_status(), 'running')
    self.assertEqual(pipeline.status, 'running')

  def test_start_single_job_fails_if_running(self):
    pipeline = models.Pipeline.create(status='running')
    job1 = models.Job.create(pipeline_id=pipeline.id)
    result = pipeline.start_single_job(job1)
    self.assertFalse(result)
    self.assertEqual(job1.status, 'idle')
    self.assertEqual(pipeline.status, 'running')

  def test_job_finished_succeeds(self):
    pipeline = models.Pipeline.create(status='running')
    models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    result = pipeline.job_finished()
    self.assertTrue(result)
    self.assertEqual(pipeline.status, 'succeeded')

  def test_job_finished_fails_if_one_remains(self):
    pipeline = models.Pipeline.create(status='running')
    models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    models.Job.create(pipeline_id=pipeline.id, status='running')
    result = pipeline.job_finished()
    self.assertFalse(result)
    self.assertEqual(pipeline.status, 'running')

  def test_job_finished_fails_if_mix_succeeded_and_failed(self):
    pipeline = models.Pipeline.create(status='running')
    job1 = models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='failed')
    models.StartCondition.create(job_id=job2.id, preceding_job_id=None)
    result = pipeline.job_finished()
    self.assertTrue(result)
    self.assertEqual(pipeline.status, 'failed')


class TestPipelineDestroy(utils.ModelTestCase):

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

  def test_import_data_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create()
    job2 = models.Job.create()
    data = {
        'params': [
            {'name': 'p1', 'type': 'string', 'value': 'foo'},
            {'name': 'p2', 'type': 'string', 'value': 'bar'},
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
    self.assertEqual(pipeline.params[0].value, 'foo')
    self.assertEqual(pipeline.params[1].name, 'p2')
    self.assertEqual(pipeline.params[1].value, 'bar')
    self.assertEqual(len(pipeline.jobs.all()), 2)
    self.assertEqual(pipeline.jobs[0].name, 'j1')
    self.assertEqual(pipeline.jobs[1].name, 'j2')


class TestJobDestroy(utils.ModelTestCase):

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

  def test_value_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, name='job1')
    job2 = models.Job.create(pipeline_id=pipeline.id, name='job2')
    sc1 = models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='success')
    self.assertEqual(sc1.value, '%s,success' % job1.id)

  def test_preceding_job_name_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, name='job1')
    job2 = models.Job.create(pipeline_id=pipeline.id, name='job2')
    sc1 = models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='success')
    self.assertEqual(sc1.preceding_job_name, 'job1')


class TestJobStartConditions(utils.ModelTestCase):

  def setUp(self):
    super(TestJobStartConditions, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJobStartConditions, self).tearDown()
    self.testbed.deactivate()

  def test_create_start_conditions_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='idle')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='idle')
    job3 = models.Job.create(pipeline_id=pipeline.id, status='idle')
    arg_start_conditions = [
      {'preceding_job_id': job1.id, 'condition': 'success'},
      {'preceding_job_id': job2.id, 'condition': 'success'},
    ]
    job3.assign_start_conditions(arg_start_conditions)
    self.assertEqual(len(job3.start_conditions), 2)

  def test_update_start_conditions_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='idle')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='idle')
    job3 = models.Job.create(pipeline_id=pipeline.id, status='idle')
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition='fail')
    arg_start_conditions = [
      {'preceding_job_id': job1.id, 'condition': 'success'},
      {'preceding_job_id': job2.id, 'condition': 'success'},
    ]
    self.assertEqual(len(job3.start_conditions), 1)
    self.assertEqual(job3.start_conditions[0].condition, 'fail')
    job3.assign_start_conditions(arg_start_conditions)
    self.assertEqual(len(job3.start_conditions), 2)
    self.assertEqual(job3.start_conditions[0].condition, 'success')
    self.assertEqual(job3.start_conditions[1].condition, 'success')

  def test_fails_if_running(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(pipeline_id=pipeline.id, status='running')
    result = job.start()
    self.assertFalse(result)

  def test_succeeds_if_waiting_without_start_conditions(self):
    pipeline = models.Pipeline.create()
    job = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    result = job.start()
    self.assertTrue(result)

  def test_succeeds_with_start_condition_fulfill_success_with_succeeded(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='success')
    result = job2.start()
    self.assertTrue(result)

  def test_fails_with_start_condition_unfulfill_success_with_failed(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='failed')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='success')
    result = job2.start()
    self.assertFalse(result)
    self.assertEqual(job2.status, 'failed')

  def test_succeeds_with_start_condition_fulfill_fail_with_failed(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='failed')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='fail')
    result = job2.start()
    self.assertTrue(result)

  def test_fails_with_start_condition_unfulfill_fail_with_succeeded(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='fail')
    result = job2.start()
    self.assertFalse(result)
    self.assertEqual(job2.status, 'failed')

  def test_succeeds_with_start_condition_fulfill_whatever_with_failed(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='failed')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='whatever')
    result = job2.start()
    self.assertTrue(result)

  def test_succeeds_with_start_condition_fulfill_whatever_with_succeeded(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='whatever')
    result = job2.start()
    self.assertTrue(result)

  def test_fails_with_start_condition_unfulfill_whatever_with_running(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='running')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='whatever')
    result = job2.start()
    self.assertFalse(result)


class TestJobStopConditions(utils.ModelTestCase):

  def test_stop_fails_with_idle(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='idle')
    result = job1.stop()
    self.assertFalse(result)
    self.assertEqual(job1.status, 'idle')

  def test_stop_fails_with_waiting(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    result = job1.stop()
    self.assertTrue(result)
    self.assertEqual(job1.status, 'failed')

  def test_stop_succeeds_with_running(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='running')
    result = job1.stop()
    self.assertTrue(result)
    self.assertEqual(job1.status, 'stopping')


class TestJobStartWithDependentJobs(utils.ModelTestCase):

  def setUp(self):
    super(TestJobStartWithDependentJobs, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    super(TestJobStartWithDependentJobs, self).tearDown()
    self.testbed.deactivate()

  def test_start_fails_with_dependent_jobs_and_expecting_success(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='failed')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    job3 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='success')
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition='success')
    result = job2.start()
    self.assertFalse(result)
    self.assertEqual(job2.status, 'failed')
    self.assertEqual(job3.status, 'failed')

  def test_start_fails_with_dependent_jobs_and_expecting_fail(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status='succeeded')
    job2 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    job3 = models.Job.create(pipeline_id=pipeline.id, status='waiting')
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition='fail')
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition='success')
    result = job2.start()
    self.assertFalse(result)
    self.assertEqual(job2.status, 'failed')
    self.assertEqual(job3.status, 'failed')
