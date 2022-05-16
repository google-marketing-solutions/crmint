# Copyright 2019 Google Inc. All rights reserved.
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

"""Module with CRMint's Commenter worker class."""


from jobs.workers import worker


class Commenter(worker.Worker):
  """Dummy worker that fails when checkbox is unchecked."""

  PARAMS = [
      ('comment', 'text', False, '', 'Comment'),
      ('success', 'boolean', True, False, 'Finish successfully'),
  ]

  def _execute(self):
    if not self._params['success']:
      raise worker.WorkerException(
          f'"{self.PARAMS[1][4]}" is unchecked: {self._params["comment"]}')
