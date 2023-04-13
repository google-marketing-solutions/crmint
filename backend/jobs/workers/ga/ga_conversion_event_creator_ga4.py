# Copyright 2023 Google Inc. All rights reserved.
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

"""Worker to create GA4 conversion events."""

from jobs.workers import worker
from jobs.workers.ga import ga_utils


class GA4ConversionEventCreator(worker.Worker):
  """Worker to create GA4 conversion events."""

  PARAMS = [
      ('ga_property_id', 'string', True, '',
       'GA Property Tracking ID (e.g. 12345)'),
      ('event_name', 'string', True, '', 'Event Name'),
  ]

  def _execute(self) -> None:
    ga_client = ga_utils.get_client('analyticsadmin', 'v1alpha')
    ga_utils.create_conversion_event_ga4(
        ga_client, self._params['ga_property_id'],
        self._params['event_name'], progress_callback=self.log_info)
