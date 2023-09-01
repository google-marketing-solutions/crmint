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

import dataclasses
from typing import Any
from controller import shared


class Source(shared.StrEnum):
  FIRST_PARTY = 'FIRST_PARTY'
  GOOGLE_ANALYTICS = 'GOOGLE_ANALYTICS'


@dataclasses.dataclass
class TimespanRange:
  """The timespan range where start and end are the number of days ago from today."""
  start: int
  end: int


class Timespan:
  """Encapsulates a timespan."""

  _training: int
  _predictive: int

  def __init__(self, timespans: list[dict[str, Any]]) -> None:
    for timespan in timespans:
      setattr(self, '_' + timespan['name'], int(timespan['value']))

  @property
  def training(self) -> TimespanRange:
    return TimespanRange(self.predictive.start + self._training + 1, self.predictive.start + 1)

  @property
  def predictive(self) -> TimespanRange:
    return TimespanRange(self._predictive + 1, 1)
