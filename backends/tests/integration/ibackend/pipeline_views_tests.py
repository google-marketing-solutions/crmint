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

from datetime import datetime
from google.appengine.ext import testbed
from google.appengine.api.taskqueue.taskqueue_stub import _BackgroundTaskScheduler, _Group, _TaskExecutor


from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from core import models
from mock import patch
from tests import utils

import threading
import requests
import time, json
import mock

class TestPipelineList(utils.IBackendBaseTest):

  def setUp(self):  
    super(TestPipelineList, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    # Activate which service we want to stub
    self.testbed.init_memcache_stub()
    self.testbed.init_app_identity_stub()
    self.testbed.init_datastore_v3_stub()

  def test_list_success(self):
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)

  def test_again_list_success(self):
    """
    This test ensure that the blueprint registration works with
    multiple tests.
    """
    response = self.client.get('/api/pipelines')
    self.assertEqual(response.status_code, 200)

# class TestPipelineParallelProcessing(utils.IBackendBaseTest):

#   def setUp(self):  
#     super(TestPipelineParallelProcessing, self).setUp()
#     self.testbed = testbed.Testbed()
#     self.testbed.activate()
#     # Activate which service we want to stub
#     self.testbed.init_memcache_stub()
#     self.testbed.init_app_identity_stub()
#     self.testbed.init_taskqueue_stub()
#     self.taskqueue_stub = self.testbed.get_stub(
#             testbed.TASKQUEUE_SERVICE_NAME)
#     # self.taskqueue_stub.StartBackgroundExecution()

#   @patch('time.sleep', return_value=None)
#   def test_pipeline_success_no_dependencies_jobs(self, patched_time_sleep):
#     """
#     This test ensures that the pipeline status is updated ('succeeded') 
#     after the successful execution (in parallel) of all the jobs.
#     """
#     pipeline = models.Pipeline.create(name="test_parallel_pipeline")
#     jobs = [models.Job.create(name=str(index), pipeline_id=pipeline.id, worker_class="WaitingWorker") 
#                 for index in range(2)]

#     params = [
#         {'id': None, 'name': 'waiting_time', 'type': 'number', 'value': '5'}
#     ]
#     relations = {'start_conditions': [], 'params': params}

#     for job in jobs:
#       job.save_relations(relations)

#     self.assertEqual(len(pipeline.jobs.all()), 2)
    
#     # necessary for starting the tasks in the background    
#     self.taskqueue_stub._auto_task_running = True

#     pipeline.start()
#     default_http_server = 'localhost'

#     # self.taskqueue_stub.StartBackgroundExecution()
#     BUILT_IN_HEADERS = set(['x-appengine-queuename',
#                         'x-appengine-taskname',
#                         'x-appengine-taskexecutioncount',
#                         'x-appengine-taskpreviousresponse',
#                         'x-appengine-taskretrycount',
#                         'x-appengine-tasketa',
#                         'x-appengine-development-payload',
#                         'content-length'])
#     for task in self.taskqueue_stub.GetTasks('default'):
#       print(task)

#       # print(task)
#       # method = task.RequestMethod_Name(task.method())

#       # headers = []
#       # for header in task["headers"]:
#       #   header_key_lower = header[0].lower()

#       #   if header_key_lower == 'host' and queue.target is not None:
#       #     headers.append(
#       #         (header[0], '.'.join([queue.target, self._default_host])))
#       #   elif header_key_lower not in BUILT_IN_HEADERS:
#       #     headers.append((header[0], header[1]))


#       # headers.append(('X-AppEngine-QueueName', "default"))
#       # headers.append(('X-AppEngine-TaskName', task["name"]))
#       # headers.append(('X-AppEngine-TaskRetryCount', 0))
#       # headers.append(('X-AppEngine-TaskETA',
#       #                 str(_UsecToSec(task.eta_usec()))))
#       # headers.append(('X-AppEngine-Fake-Is-Admin', '1'))
#       # headers.append(('Content-Length', str(len(task["body"]))))

#       # if task.has_body() and ('content-type' not in [key.lower() for key, _ in headers]):
#       #   headers.append(('Content-Type', 'application/octet-stream'))

#       # headers.append(('X-AppEngine-TaskExecutionCount', str(task.execution_count())))
#       # if task.has_runlog() and task.runlog().has_response_code():
#       #   headers.append(('X-AppEngine-TaskPreviousResponse',
#       #                 str(task.runlog().response_code())))

#       print(int(dict(task["headers"]).get('X-AppEngine-TaskExecutionCount')))
#       print(dict(task["headers"]))
#       headers  = dict(task["headers"])
#       print(headers)
#       import ipdb
#       # ipdb.set_trace(context=5)
#       s = requests.Session()
#       retry = Retry(connect=3, backoff_factor=0.5)
#       adapter = HTTPAdapter(max_retries=retry)
#       s.mount("http://", adapter)
#       retries = 5
#       while retries !=0:
#         try:
#           # ipdb.set_trace(context=6)

#           response = s.post(
#             # "http://localhost:8081" + task["url"], data={}, headers = headers
#             "http://localhost:42337" + task["url"], data={}, headers=headers
#           )
#           retries = 0
#           print(response)
#         except Exception as e:
#           time.sleep(5)
#           print("sleeping...")
#           print(e)
#           retries -= 1

#       # print(response.text)
#       # print(response.status_code)
#       # print(response.content)

#     patched_time_sleep(55)

#     result = pipeline.job_finished()
#     self.assertTrue(result)
#     self.assertEqual(pipeline.status, 'succeeded')


class TestPipelineParallelProcessing(utils.IBackendBaseTest):
  
  @patch('time.sleep', return_value=None)
  @patch('core.logging.logger')
  def _mocked_task(self, duration, job, output, patched_logger, patched_time_sleep):
    patched_logger.log_struct.__name__ = 'foo'


    job.enqueued_workers_count += 1
    
    job.succeeded_workers_count = 0
    job.failed_workers_count = 0
    job.status = 'running'
    job.status_changed_at = datetime.now()
    job.save()
    print(str(job) + " started")
    # worker.execute()
    patched_time_sleep(duration)
    
    job.worker_succeeded()
    print("worker succeeded back")

    output.put(job)

  def _mocked_taskqueue(self, duration, jobs):
    import multiprocessing as mp
    output = mp.Queue()
    tasks = [mp.Process(target = self._mocked_task, args=(duration, job, output)) for index,job in enumerate(jobs)]
    for task in tasks:
      task.start()

    print("back to join tasks")
    time.sleep(15)
    print("waited")
    for task in tasks:
      task.join()
    print("tasks joined")
    results = [output.get() for task in tasks]
    return True


  @patch('core.models.Job.run')
  @patch('core.logging.logger')
  @patch('time.sleep', return_value=None)
  def test_success_pipeline_finish_no_job_dependencies(self, patched_time_sleep, patched_logger, patched_job_run):
    """
    This test ensures that the pipeline status is updated ('succeeded') 
    after the successful execution of all the jobs.
    """
    patched_logger.log_struct.__name__ = 'foo'

    pipeline = models.Pipeline.create()
    jobs = [models.Job.create(name=str(index), pipeline_id=pipeline.id) 
                for index in range(2)]
    for job in jobs:
      job.save()

    patched_job_run.side_effect = lambda: self._mocked_taskqueue(5, jobs)

    self.assertEqual(len(pipeline.jobs.all()), 2)
    
    pipeline.start()
    patched_time_sleep(10)
    result = pipeline.job_finished()
    self.assertTrue(result)
    self.assertEqual(pipeline.status, 'succeeded')