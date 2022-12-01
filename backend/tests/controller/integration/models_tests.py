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

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from common import crmint_logging
from common import task
from controller import models
from tests import controller_utils


class ModelTestCase(controller_utils.ModelTestCase):

  def setUp(self):
    super().setUp()
    self.patched_task_enqueue = self.enter_context(
        mock.patch.object(task.Task, 'enqueue', autospec=True))
    self.patched_log_message = self.enter_context(
        mock.patch.object(crmint_logging, 'log_message', autospec=True))
    self.patched_log_pipeline_status = self.enter_context(
        mock.patch.object(crmint_logging, 'log_pipeline_status', autospec=True))


class TestPipelineWithJobs(ModelTestCase):

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

  @parameterized.named_parameters(
      ('One job idle', models.Job.STATUS.IDLE),
      ('One job succeeded', models.Job.STATUS.SUCCEEDED),
      ('One job failed', models.Job.STATUS.FAILED),
  )
  def test_start_succeeds_with_different_job_states(self, job1_status):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, status=job1_status)
    result = pipeline.start()
    self.assertEqual(result, True)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)

  @parameterized.named_parameters(
      ('One job running', models.Job.STATUS.RUNNING),
      ('One job stopping', models.Job.STATUS.STOPPING),
  )
  def test_start_fails_with_different_job_states(self, job1_status):
    pipeline = models.Pipeline.create()
    _ = models.Job.create(pipeline_id=pipeline.id, status=job1_status)
    result = pipeline.start()
    self.assertEqual(result, False)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.FAILED)

  def test_start_fails_with_pipeline_if_unknown_parameter(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id, worker_class='Foo')
    models.Param.create(
        job_id=job1.id,
        name='field1',
        type='number',
        value='{% VAR_FOO %}')  # initialize with a non-boolean value
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    pipeline.start()
    self.patched_log_message.assert_called_once_with(
        'Invalid job parameter "None": \'VAR_FOO\' is undefined',
        log_level='ERROR',
        worker_class='Foo',
        pipeline_id=pipeline.id,
        job_id=job1.id)
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.FAILED)

  def test_stop_fails_if_not_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.IDLE)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)
    result = pipeline.stop()
    self.assertEqual(result, False)

  def test_stop_succeeds_and_stop_all_jobs(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.RUNNING)
    models.Job.create(pipeline_id=pipeline.id, status=models.Job.STATUS.RUNNING)
    stopping = pipeline.stop()
    self.assertTrue(stopping)
    self.assertEqual(pipeline.jobs[0].status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(pipeline.jobs[1].status, models.Job.STATUS.STOPPING)
    self.assertEqual(pipeline.jobs[2].status, models.Job.STATUS.STOPPING)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.STOPPING)

  def test_stop_dependent_jobs(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.IDLE)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    pipeline.start()
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    stopping = pipeline.stop()
    self.assertTrue(stopping)
    self.assertEqual(job1.status, models.Job.STATUS.STOPPING)
    self.assertEqual(job2.status, models.Job.STATUS.IDLE)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.STOPPING)
    task1 = models.TaskEnqueued.all()[0]
    job1.task_succeeded(task1.name)
    self.assertEqual(job1._enqueued_task_count(), 0)
    self.assertEqual(job1.status, models.Job.STATUS.SUCCEEDED)
    self.assertEqual(job2.status, models.Job.STATUS.IDLE)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.IDLE)

  def test_stopping_one_job_should_not_start_dependent_jobs(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    task1 = job1.start()
    self.assertIsNotNone(task1)
    stopping = job1.stop()
    self.assertTrue(stopping)
    self.assertEqual(job1.status, models.Job.STATUS.STOPPING)
    self.assertEqual(job1._enqueued_task_count(), 1)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    self.assertEqual(job2._enqueued_task_count(), 0)
    job1.task_failed(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(job1._enqueued_task_count(), 0)

  def test_inactive_job_unaffected_by_incoming_finished_task(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.IDLE)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    job1.task_succeeded('untracked_task_name')
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)

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
    # We set failed, to notify the user in the UI.
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.FAILED)

  def test_pipeline_failing_without_conditions_should_cancel_all_tasks(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    with self.subTest('Job 1 starts'):
      task1 = job1.start()
      self.assertIsNotNone(task1)
      self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
      self.assertEqual(job1._enqueued_task_count(), 1)
    with self.subTest('Job 2 starts'):
      task2 = job2.start()
      self.assertIsNotNone(task2)
      self.assertEqual(job2.status, models.Job.STATUS.RUNNING)
      self.assertEqual(job2._enqueued_task_count(), 1)
    with self.subTest('Job 2 failed'):
      job2.task_failed(task2.name)
      self.assertEqual(job2.status, models.Job.STATUS.FAILED)
      self.assertEqual(job2._enqueued_task_count(), 0)
      self.assertEqual(pipeline.status, models.Pipeline.STATUS.FAILED)
      # It should trigger the end of the pipeline by itself
      self.assertEqual(job1.status, models.Job.STATUS.STOPPING)
      self.assertEqual(job1._enqueued_task_count(), 1)
      job1.task_succeeded(task1.name)
      self.assertEqual(job1.status, models.Job.STATUS.SUCCEEDED)
      self.assertEqual(job1._enqueued_task_count(), 0)


class TestPipelineFinishingStatus(ModelTestCase):

  @parameterized.named_parameters(
      ('Pipeline is finished if isolated job succeeded',
       models.Job.STATUS.SUCCEEDED,
       models.Pipeline.STATUS.SUCCEEDED),
      ('Pipeline failed if isolated job failed',
       models.Job.STATUS.FAILED,
       models.Pipeline.STATUS.FAILED),
  )
  def test_pipeline_state_with_isolated_job(self, job_status, pipeline_status):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    unused_isolated_job = models.Job.create(
        pipeline_id=pipeline.id, status=job_status)
    pipeline.leaf_job_finished()
    self.assertEqual(pipeline.status, pipeline_status)

  @parameterized.named_parameters(
      ('Pipeline is finished if all jobs succeeded',
       models.Job.STATUS.SUCCEEDED,
       models.StartCondition.CONDITION.SUCCESS,
       models.Job.STATUS.SUCCEEDED,
       models.Pipeline.STATUS.SUCCEEDED),
      ('Pipeline not finished if one job remains',
       models.Job.STATUS.RUNNING,
       models.StartCondition.CONDITION.WHATEVER,
       models.Job.STATUS.WAITING,
       models.Pipeline.STATUS.RUNNING),
      ('Pipeline failed if one job failed',
       models.Job.STATUS.FAILED,
       models.StartCondition.CONDITION.SUCCESS,
       models.Job.STATUS.WAITING,
       models.Pipeline.STATUS.FAILED),
      ('Pipeline not finished if last job remains running',
       models.Job.STATUS.SUCCEEDED,
       models.StartCondition.CONDITION.WHATEVER,
       models.Job.STATUS.RUNNING,
       models.Pipeline.STATUS.RUNNING),
      ('Pipeline failed if a leaf job failed',
       models.Job.STATUS.SUCCEEDED,
       models.StartCondition.CONDITION.SUCCESS,
       models.Job.STATUS.FAILED,
       models.Pipeline.STATUS.FAILED),
      ('Pipeline is finished if stopped after first job',
       models.Job.STATUS.IDLE,
       models.StartCondition.CONDITION.SUCCESS,
       models.Job.STATUS.IDLE,
       models.Pipeline.STATUS.IDLE),
  )
  def test_pipeline_state_with_starting_condition(self,
                                                  job2_status,
                                                  job3_starting_condition,
                                                  job3_status,
                                                  pipeline_status):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.SUCCEEDED)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=job2_status)
    job3 = models.Job.create(
        pipeline_id=pipeline.id, status=job3_status)
    cond1 = models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    cond2 = models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=job3_starting_condition)
    pipeline.leaf_job_finished()
    self.assertEqual(pipeline.status, pipeline_status)

  @parameterized.named_parameters(
      ('Finished with success',
       models.Job.STATUS.SUCCEEDED,
       models.Pipeline.STATUS.SUCCEEDED),
      ('Finished with failure',
       models.Job.STATUS.FAILED,
       models.Pipeline.STATUS.FAILED),
  )
  def test_log_for_notification_on_finished_state(self,
                                                  job_status,
                                                  pipeline_status):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    task1 = job1.start()
    job1._task_finished(task1.name, job_status)
    self.assertNotEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)
    self.patched_log_pipeline_status.assert_called_once_with(
        mock.ANY, pipeline_status=pipeline_status, pipeline_id=mock.ANY)

  @parameterized.named_parameters(
      ('Finished with success',
       models.Job.STATUS.SUCCEEDED, models.Pipeline.STATUS.IDLE),
      ('Finished with failure',
       models.Job.STATUS.FAILED, models.Pipeline.STATUS.FAILED),
  )
  def test_pipeline_state_when_starting_single_job(self,
                                                   job_status,
                                                   pipeline_status):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.IDLE)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    job3 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    task1 = pipeline.start_single_job(job2)
    self.assertEqual(job2.status, models.Job.STATUS.RUNNING)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)
    job2._task_finished(task1.name, job_status)
    self.assertEqual(job2.status, job_status)
    self.assertEqual(pipeline.status, pipeline_status)


class TestPipelineDestroy(ModelTestCase):

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


class TestPipelineImport(ModelTestCase):

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
    self.assertLen(pipeline.params, 2)
    self.assertEqual(pipeline.params[0].name, 'p1')
    self.assertEqual(pipeline.params[0].label, 'P1')
    self.assertEqual(pipeline.params[0].value, 'foo')
    self.assertEqual(pipeline.params[1].name, 'p2')
    self.assertEqual(pipeline.params[1].label, 'P2')
    self.assertEqual(pipeline.params[1].value, 'bar')
    self.assertLen(pipeline.jobs, 2)
    self.assertEqual(pipeline.jobs[0].name, 'j1')
    self.assertEqual(pipeline.jobs[1].name, 'j2')


class TestJobStartedStatus(ModelTestCase):

  def test_succeeds_status_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    started = job.start()
    self.assertIsNotNone(started)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)

  def test_fails_if_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.RUNNING)
    self.assertIsNone(job.start())

  def test_single_fails_if_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.RUNNING)
    with self.assertRaises(RuntimeError):
      job.start_as_single()


class TestJobDestroy(ModelTestCase):

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


class TestStartConditionWithJobs(ModelTestCase):

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


class TestJobStartConditions(ModelTestCase):

  def test_create_start_conditions_succeeds(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    job3 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.IDLE)
    arg_start_conditions = [
        {
            'preceding_job_id': job1.id,
            'condition': models.StartCondition.CONDITION.SUCCESS
        },
        {
            'preceding_job_id': job2.id,
            'condition': models.StartCondition.CONDITION.SUCCESS
        },
    ]
    job3.assign_start_conditions(arg_start_conditions)
    self.assertLen(job3.start_conditions, 2)

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
            'condition': models.StartCondition.CONDITION.SUCCESS
        },
        {
            'preceding_job_id': job2.id,
            'condition': models.StartCondition.CONDITION.SUCCESS
        },
    ]
    self.assertLen(job3.start_conditions, 1)
    self.assertEqual(job3.start_conditions[0].condition,
                     models.StartCondition.CONDITION.FAIL)
    job3.assign_start_conditions(arg_start_conditions)
    self.assertLen(job3.start_conditions, 2)
    self.assertEqual(job3.start_conditions[0].condition,
                     models.StartCondition.CONDITION.SUCCESS)
    self.assertEqual(job3.start_conditions[1].condition,
                     models.StartCondition.CONDITION.SUCCESS)

  def test_succeeds_if_waiting_without_start_conditions(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    task1 = job.start()
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    self.assertIsNotNone(task1)

  @parameterized.named_parameters(
      {
          'testcase_name': 'Fulfilled success condition',
          'job1_status': models.Job.STATUS.SUCCEEDED,
          'job2_starting_condition': models.StartCondition.CONDITION.SUCCESS,
          'job2_status': models.Job.STATUS.RUNNING,
          'pipeline_status': models.Pipeline.STATUS.RUNNING,
      },
      {
          'testcase_name': 'Unfulfilled success condition',
          'job1_status': models.Job.STATUS.FAILED,
          'job2_starting_condition': models.StartCondition.CONDITION.SUCCESS,
          'job2_status': models.Job.STATUS.IDLE,
          'pipeline_status': models.Pipeline.STATUS.FAILED,
      },
      {
          'testcase_name': 'Fulfilled fail condition',
          'job1_status': models.Job.STATUS.FAILED,
          'job2_starting_condition': models.StartCondition.CONDITION.FAIL,
          'job2_status': models.Job.STATUS.RUNNING,
          'pipeline_status': models.Pipeline.STATUS.RUNNING,
      },
      {
          'testcase_name': 'Unfulfilled fail condition',
          'job1_status': models.Job.STATUS.SUCCEEDED,
          'job2_starting_condition': models.StartCondition.CONDITION.FAIL,
          'job2_status': models.Job.STATUS.IDLE,
          'pipeline_status': models.Pipeline.STATUS.FAILED,
      },
      {
          'testcase_name': 'Fulfilled whatever condition with job1 success',
          'job1_status': models.Job.STATUS.SUCCEEDED,
          'job2_starting_condition': models.StartCondition.CONDITION.WHATEVER,
          'job2_status': models.Job.STATUS.RUNNING,
          'pipeline_status': models.Pipeline.STATUS.RUNNING,
      },
      {
          'testcase_name': 'Fulfilled whatever condition with job1 failure',
          'job1_status': models.Job.STATUS.FAILED,
          'job2_starting_condition': models.StartCondition.CONDITION.WHATEVER,
          'job2_status': models.Job.STATUS.RUNNING,
          'pipeline_status': models.Pipeline.STATUS.RUNNING,
      },
  )
  def test_succeeds_fulfilling_starting_condition(self,
                                                  job1_status,
                                                  job2_starting_condition,
                                                  job2_status,
                                                  pipeline_status):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=job2_starting_condition)
    task1 = job1.start()
    self.assertEqual(job1.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job2.status, models.Job.STATUS.WAITING)
    job1._task_finished(task1.name, job1_status)
    self.assertEqual(job1.status, job1_status)
    self.assertEqual(job2.status, job2_status)
    self.assertEqual(pipeline.status, pipeline_status)


class TestJobStopConditions(ModelTestCase):

  def test_stop_fails_with_idle(self):
    pipeline = models.Pipeline.create()
    job1 = models.Job.create(pipeline_id=pipeline.id)
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)
    result = job1.stop()
    self.assertFalse(result)
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)

  def test_stop_reset_to_idle(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    result = job1.stop()
    self.assertFalse(result)
    self.assertEqual(job1.status, models.Job.STATUS.IDLE)

  def test_stop_succeeds_with_running(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertIsNotNone(task1)
    self.assertTrue(job1.stop())
    self.assertEqual(job1.status, models.Job.STATUS.STOPPING)
    job1.task_succeeded(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.SUCCEEDED)

  def test_stop_succeeds_with_outdated_tasks(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    task1 = job1.start()
    self.assertIsNotNone(task1)
    self.assertLen(models.TaskEnqueued.all(), 1)
    # Removes all tasks to simulate a duplicated pub/sub message for example.
    models.TaskEnqueued.query.delete()
    self.assertTrue(job1.stop())
    self.assertEqual(job1.status, models.Job.STATUS.STOPPING)


class TestJobStartWithDependentJobs(ModelTestCase):

  @parameterized.named_parameters(
      ('Expecting success',
       models.StartCondition.CONDITION.SUCCESS,
       models.Job.STATUS.FAILED),
      ('Expecting failure',
       models.StartCondition.CONDITION.FAIL,
       models.Job.STATUS.SUCCEEDED),
  )
  def test_start_fails_with_dependent_jobs_and_expecting_success(
      self, job2_starting_condition, job1_status):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job3 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=job2_starting_condition)
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    task1 = job1.start()
    self.assertIsNotNone(task1)
    job1._task_finished(task1.name, job1_status)
    self.assertEqual(job1.status, job1_status)
    self.assertEqual(job2.status, models.Job.STATUS.IDLE)
    self.assertEqual(job3.status, models.Job.STATUS.IDLE)

  def test_dependent_job_starts_after_multiple_workers_finish_with_fail(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job3 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.FAIL)
    models.StartCondition.create(
        job_id=job3.id,
        preceding_job_id=job2.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    task1 = job1.start()
    task2 = job1.enqueue(job1.worker_class, {})
    self.assertIsNotNone(task1)
    job1.task_succeeded(task1.name)
    job1.task_failed(task2.name)  # Only second worker failed
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(job2.status, models.Job.STATUS.RUNNING)
    self.assertEqual(job3.status, models.Job.STATUS.WAITING)


class TestJobStartingMultipleTasks(ModelTestCase):

  def test_succeeds_completing_tasks_in_series(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    worker_params = dict([(p.name, p.val) for p in job.params])
    task1 = job.start()
    self.assertIsNotNone(task1)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    task2 = job.enqueue(job.worker_class, worker_params)
    self.assertIsNotNone(task2)
    job.task_succeeded(task1.name)
    self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    job.task_succeeded(task2.name)
    self.assertEqual(job.status, models.Job.STATUS.SUCCEEDED)

  def test_pipeline_fails_when_failing_condition(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.SUCCESS)
    task1 = job1.start()
    job1.task_failed(task1.name)
    self.assertEqual(job1.status, models.Job.STATUS.FAILED)
    self.assertEqual(job2.status, models.Job.STATUS.IDLE)
    self.assertEqual(pipeline.status, models.Pipeline.STATUS.FAILED)

  @parameterized.named_parameters(
      ('Job1 failed', models.Job.STATUS.FAILED),
      ('Job1 succeeded', models.Job.STATUS.SUCCEEDED),
  )
  def test_pipeline_succeeds_with_whatever_condition(self, job1_status):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    job2 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    models.StartCondition.create(
        job_id=job2.id,
        preceding_job_id=job1.id,
        condition=models.StartCondition.CONDITION.WHATEVER)
    task1 = job1.start()
    with self.subTest('Job 1 finished'):
      job1_remaining_tasks = job1._task_finished(task1.name, job1_status)
      self.assertEqual(job1_remaining_tasks, 0)
      self.assertEqual(job2._enqueued_task_count(), 1)
      job2_ns = job2._get_task_namespace()
      task2 = models.TaskEnqueued.where(task_namespace=job2_ns).all()[0]
      self.assertEqual(job1.status, job1_status)
      self.assertEqual(job2.status, models.Job.STATUS.RUNNING)
      self.assertEqual(pipeline.status, models.Pipeline.STATUS.RUNNING)
    with self.subTest('Job 1 failed'):
      job2.task_succeeded(task2.name)
      self.assertEqual(job1.status, job1_status)
      self.assertEqual(job2.status, models.Job.STATUS.SUCCEEDED)
      self.assertFalse(pipeline.has_failed())
      self.assertEqual(pipeline.status, models.Pipeline.STATUS.SUCCEEDED)

  def test_succeeds_completing_tasks_in_parallel(self):
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    worker_params = dict([(p.name, p.val) for p in job.params])
    with self.subTest('Starts job'):
      task1 = job.start()
      self.assertIsNotNone(task1)
      self.assertEqual(job.status, models.Job.STATUS.RUNNING)
    with self.subTest('Tasks are enqueued'):
      task2 = job.enqueue(job.worker_class, worker_params)
      task3 = job.enqueue(job.worker_class, worker_params)
      self.assertTrue(task2)
      self.assertTrue(task3)
    with self.subTest('Tasks are enqueued'):
      job.task_succeeded(task1.name)
      self.assertEqual(job.status, models.Job.STATUS.RUNNING)
      job.task_succeeded(task3.name)
      self.assertEqual(job.status, models.Job.STATUS.RUNNING)
      job.task_succeeded(task2.name)
      self.assertEqual(job.status, models.Job.STATUS.SUCCEEDED)


if __name__ == '__main__':
  absltest.main()
