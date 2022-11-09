# Copyright 2020 Google Inc
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

import signal
import sys
import traceback
import types

from flask import json
from flask.app import Flask
from flask.globals import request

from common import auth_filter
from common import crmint_logging
from common import message
from common import result
from common import task
from jobs.workers import finder
from jobs.workers import worker

app = Flask(__name__)
auth_filter.add(app)


@app.route('/liveness_check', methods=['GET'])
def liveness_check():
  return 'OK'


@app.route('/readiness_check', methods=['GET'])
def readiness_check():
  return 'OK'


@app.route('/api/workers', methods=['GET'])
def workers_list():
  return (json.jsonify(list(finder.WORKERS_MAPPING.keys())),
          {'Access-Control-Allow-Origin': '*'})


@app.route('/api/workers/<worker_class>/params', methods=['GET'])
def worker_parameters(worker_class):
  klass = finder.get_worker_class(worker_class)
  keys = ['name', 'type', 'required', 'default', 'label']
  return (json.jsonify([dict(zip(keys, param)) for param in klass.PARAMS]),
          {'Access-Control-Allow-Origin': '*'})


@app.route('/push/start-task', methods=['POST'])
def start_task():
  """Receives a task from Pub/Sub and executes it."""
  try:
    task_inst = task.Task.from_request(request)
  except (message.BadRequestError, message.TooEarlyError) as e:
    return e.message, e.code

  crmint_logging.log_message(
      f'Starting task for name: {task_inst.name}',
      log_level='DEBUG',
      worker_class=task_inst.worker_class,
      pipeline_id=task_inst.pipeline_id,
      job_id=task_inst.job_id)

  worker_class = finder.get_worker_class(task_inst.worker_class)
  worker_params = task_inst.worker_params.copy()
  for setting in worker_class.GLOBAL_SETTINGS:
    worker_params[setting] = task_inst.general_settings[setting]
  worker_inst = worker_class(
      worker_params, task_inst.pipeline_id, task_inst.job_id)

  try:
    workers_to_enqueue = worker_inst.execute()
    crmint_logging.log_message(
        f'Executed task for name: {task_inst.name}',
        log_level='DEBUG',
        worker_class=task_inst.worker_class,
        pipeline_id=task_inst.pipeline_id,
        job_id=task_inst.job_id)
  except worker.WorkerException as e:
    class_name = e.__class__.__name__
    worker_inst.log_error(f'Execution failed: {class_name}: {e}')
    result_inst = result.Result(task_inst.name, task_inst.job_id, False)
    result_inst.report()
  except Exception as e:  # pylint: disable=broad-except
    formatted_exception = traceback.format_exc()
    worker_inst.log_error(f'Unexpected error {formatted_exception}')
    if task_inst.attempts < worker_inst.MAX_ATTEMPTS:
      task_inst.reenqueue()
    else:
      worker_inst.log_error(f'Giving up after {task_inst.attempts} attempt(s)')
      result_inst = result.Result(task_inst.name, task_inst.job_id, False)
      result_inst.report()
  else:
    result_inst = result.Result(
        task_inst.name, task_inst.job_id, True, workers_to_enqueue)
    result_inst.report()
  return 'OK', 200


def shutdown_handler(sig: int, frame: types.FrameType) -> None:
  """Gracefully shuts down the instance.

  Within the 3 seconds window, try to do as much as possible:
    1. Commit all pending Pub/Sub messages (as much as possible).

  You can read more about this practice:
  https://cloud.google.com/blog/topics/developers-practitioners/graceful-shutdowns-cloud-run-deep-dive.

  Args:
    sig: Signal intercepted.
    frame: Frame object such as `tb.tb_frame` if `tb` is a traceback object.
  """
  del sig, frame  # Unused argument
  crmint_logging.log_global_message(
      'Signal received, safely shutting down.',
      log_level='WARNING')
  message.shutdown()
  sys.exit(0)


if __name__ == '__main__':
  signal.signal(signal.SIGINT, shutdown_handler)  # Handles Ctrl-C locally.
  app.run(host='0.0.0.0', port=8081, debug=True)
elif not app.config.get('DEBUG', False):
  # Handles App Engine instance termination.
  signal.signal(signal.SIGTERM, shutdown_handler)
