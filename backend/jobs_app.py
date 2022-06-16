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


from traceback import format_exc
from flask import Flask, json, request
from common import auth_filter
from common.message import BadRequestError, TooEarlyError
from common.task import Task
from common.result import Result
from jobs import workers
from jobs.workers.worker import WorkerException


app = Flask(__name__)
auth_filter.add(app)


@app.route('/api/workers', methods=['GET'])
def workers_list():
  return json.jsonify(workers.EXPOSED), {'Access-Control-Allow-Origin': '*'}


@app.route('/api/workers/<worker_class>/params', methods=['GET'])
def worker_parameters(worker_class):
  klass = workers.find(worker_class)
  keys = ['name', 'type', 'required', 'default', 'label']
  return (json.jsonify([dict(zip(keys, param)) for param in klass.PARAMS]),
          {'Access-Control-Allow-Origin': '*'})


@app.route('/push/start-task', methods=['POST'])
def start_task():
  try:
    task = Task.from_request(request)
  except (BadRequestError, TooEarlyError) as e:
    return e.message, e.code

  worker_class = workers.find(task.worker_class)
  worker_params = task.worker_params.copy()
  for setting in worker_class.GLOBAL_SETTINGS:
    worker_params[setting] = task.general_settings[setting]
  worker = worker_class(worker_params, task.pipeline_id, task.job_id)

  try:
    workers_to_enqueue = worker.execute()
  except WorkerException as e:
    class_name = e.__class__.__name__
    worker.log_error(f'Execution failed: {class_name}: {e}')
    result = Result(task.name, task.job_id, False)
    result.report()
  except Exception as e:  # pylint: disable=broad-except
    formatted_exception = format_exc()
    worker.log_error(f'Unexpected error {formatted_exception}')
    if task.attempts < worker.MAX_ATTEMPTS:
      task.reenqueue()
    else:
      worker.log_error(f'Giving up after {task.attempts} attempt(s)')
      result = Result(task.name, task.job_id, False)
      result.report()
  else:
    result = Result(task.name, task.job_id, True, workers_to_enqueue)
    result.report()
  return 'OK', 200


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8081, debug=True)
