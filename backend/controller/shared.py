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

from enum import Enum

"""Shared definitions."""


class PipelineStatus:
  IDLE = 'idle'
  FAILED = 'failed'
  SUCCEEDED = 'succeeded'
  STOPPING = 'stopping'
  RUNNING = 'running'


class JobStatus:
  IDLE = 'idle'
  FAILED = 'failed'
  SUCCEEDED = 'succeeded'
  RUNNING = 'running'
  WAITING = 'waiting'
  STOPPING = 'stopping'


# TODO: Leverage StrEnum in core lib once available in a later version (3.11) of python.
class StrEnum(str, Enum):
  def __str__(self) -> str:
    return str(self.value)

  def __eq__(self, other) -> bool:
    return other == str(self.value)