# Copyright 2020 Google Inc. All rights reserved.
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

"""Legacy worker runnig BQML queries; please use BQScriptExecutor instead."""


from jobs.workers.bigquery import bq_script_executor


class BQMLTrainer(bq_script_executor.BQScriptExecutor):
  """Worker to run a BQML query.

  *Deprecated since CRMint 2.0:* Switch to the new `BQScriptExecutor` worker.
  """

  def _execute(self) -> None:
    self.log_warn('Deprepcated: BQMLTrainer has been deprecated, please '
                  'upgrade to the new BQScriptExecutor worker.')
    super()._execute()
