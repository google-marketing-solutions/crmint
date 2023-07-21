# Copyright 2023 Google Inc
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

"""MlModel shared classes."""

from typing import Any
from controller import shared


class Source(shared.StrEnum):
  FIRST_PARTY = 'FIRST_PARTY'
  GOOGLE_ANALYTICS = 'GOOGLE_ANALYTICS'


class Timespan:
  """Encapsulates a timespan."""

  _training: int
  _predictive: int

  def __init__(self, timespans: list[dict[str, Any]]) -> None:
    for timespan in timespans:
      setattr(self, '_' + timespan['name'], int(timespan['value']))

  @property
  def training_start(self) -> int:
    return self.predictive_start + self._training + 1

  @property
  def training_end(self) -> int:
    return self.predictive_start + 1

  @property
  def predictive_start(self) -> int:
    return self._predictive + 1

  @property
  def predictive_end(self) -> int:
    return 1