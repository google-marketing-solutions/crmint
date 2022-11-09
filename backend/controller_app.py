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

"""Create a controller instance."""

import signal
import sys
import types

import flask_tasks
from common import auth_filter
from common import crmint_logging
from common import message
from controller import app as app_factory
from controller import database
from controller import extensions

app = app_factory.create_app()
flask_tasks.add(app)
auth_filter.add(app)


@app.route('/liveness_check', methods=['GET'])
def liveness_check():
  return 'OK'


@app.route('/readiness_check', methods=['GET'])
def readiness_check():
  extensions.db.engine.execute('SELECT 1')
  return 'OK'


def shutdown_handler(sig: int, frame: types.FrameType) -> None:
  """Gracefully shuts down the instance.

  Within the 3 seconds window, try to do as much as possible:
    1. Commit all pending Pub/Sub messages (as much as possible).
    2. Drop all connections to the database.

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
  database.shutdown(app)
  sys.exit(0)


if __name__ == '__main__':
  signal.signal(signal.SIGINT, shutdown_handler)  # Handles Ctrl-C locally.
  app.run(host='0.0.0.0', port=8080, debug=True)
elif not app.config.get('DEBUG', False):
  # Handles App Engine instance termination.
  signal.signal(signal.SIGTERM, shutdown_handler)
