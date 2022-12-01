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

import base64
import json
from typing import Any, Tuple
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
import freezegun

from common import crmint_logging
from controller import models
from tests import controller_utils


def _create_pubsub_encoded_result_payload(
    *,
    task_name: str,
    success: bool,
    workers_to_enqueue: list[Tuple[str, dict[str, Any], int]]
    ) -> dict[str, Any]:
  """Returns a payload with an encoded message, like PubSub would do."""
  data = {
      'task_name': task_name,
      'job_id': 1,
      'success': success,
      'workers_to_enqueue': workers_to_enqueue,
  }
  data_encoded = base64.b64encode(json.dumps(data).encode('utf8'))
  payload = {
      'message': {
          'attributes': {
              'start_time': 1434636430,  # 9 seconds before 2015-06-18T16:07:19
          },
          'data': data_encoded.decode('utf8'),
      }
  }
  return payload


@freezegun.freeze_time('2015-06-18T16:07:19')
class TestResultViews(controller_utils.ControllerAppTest):

  @parameterized.named_parameters(
      {
          'testcase_name': 'Result with success',
          'success': True,
          'workers_to_enqueue': [],
          'expected_job_status': models.Job.STATUS.SUCCEEDED,
          'expected_enqueing_count': 0
      },
      {
          'testcase_name': 'Result with failure',
          'success': False,
          'workers_to_enqueue': [],
          'expected_job_status': models.Job.STATUS.FAILED,
          'expected_enqueing_count': 0
      },
      {
          'testcase_name': 'Enqueuing on success',
          'success': True,
          'workers_to_enqueue': [('WorkerA', {}, 0), ('WorkerB', {}, 0)],
          'expected_job_status': models.Job.STATUS.RUNNING,
          'expected_enqueing_count': 2
      },
      {
          'testcase_name': 'No enqueuing on failure',
          'success': False,
          'workers_to_enqueue': [('WorkerA', {}, 0), ('WorkerB', {}, 0)],
          'expected_job_status': models.Job.STATUS.FAILED,
          'expected_enqueing_count': 0
      },
  )
  def test_result_with_success(self,
                               success,
                               workers_to_enqueue,
                               expected_job_status,
                               expected_enqueing_count):
    patched_log_pipeline_status = self.enter_context(
        mock.patch.object(crmint_logging, 'log_pipeline_status', autospec=True))
    pipeline = models.Pipeline.create(status=models.Pipeline.STATUS.RUNNING)
    job1 = models.Job.create(
        pipeline_id=pipeline.id, status=models.Job.STATUS.WAITING)
    task1 = job1.start()
    payload = _create_pubsub_encoded_result_payload(
        task_name=task1.name,
        success=success,
        workers_to_enqueue=workers_to_enqueue)
    response = self.client.post('/push/task-finished', json=payload)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(job1.status, expected_job_status)
    self.assertEqual(job1._enqueued_task_count(), expected_enqueing_count)


if __name__ == '__main__':
  absltest.main()
