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


from flask import Flask, json
from common import auth_filter
from jobs import workers


app = Flask(__name__)
auth_filter.add(app)


@app.route('/api/workers', methods=['GET'])
def workers_list():
  return json.jsonify(workers.AVAILABLE), {'Access-Control-Allow-Origin': '*'}


@app.route('/api/workers/<worker_class>/params', methods=['GET'])
def worker_params(worker_class):
  klass = getattr(workers, worker_class)
  keys = ['name', 'type', 'required', 'default', 'label']
  return (json.jsonify([dict(zip(keys, param)) for param in klass.PARAMS]),
          {'Access-Control-Allow-Origin': '*'})


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8081, debug=True)
