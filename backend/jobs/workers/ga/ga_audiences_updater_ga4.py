# Copyright 2022 Google Inc. All rights reserved.
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

"""Worker to update Google Analytics remarketing audiences."""

from google.cloud import bigquery

from jobs.workers.bigquery import bq_worker
from jobs.workers.ga import ga_utils


class GA4AudiencesUpdater(bq_worker.BQWorker):
  """Worker to update GA4 audiences using values from a BigQuery table."""

  PARAMS = [
      ('ga_property_id', 'string', True, '',
       'GA Property Tracking ID (e.g. 12345)'),
      ('bq_project_id', 'string', False, '', 'BQ Project ID'),
      ('bq_dataset_id', 'string', True, '', 'BQ Dataset ID'),
      ('bq_table_id', 'string', True, '', 'BQ Table ID'),
      ('bq_dataset_location', 'string', False, '', 'BQ Dataset Location'),
      ('template', 'text', True, '',
       'JSON template to create/update a GA4 audience'),
  ]

  def _execute(self) -> None:
    bq_client = self._get_client()
    dataset_ref = bigquery.DatasetReference(
        self._params['bq_project_id'], self._params['bq_dataset_id'])
    table_ref = bigquery.TableReference(dataset_ref,
                                        self._params['bq_table_id'])
    patches = ga_utils.get_audience_patches(
        bq_client, table_ref, self._params['template'])
    self.log_info(f'Retrieved #{len(patches)} audience configs from BigQuery')
    ga_client = ga_utils.get_client('analyticsadmin', 'v1alpha')
    audiences = ga_utils.fetch_audiences_ga4(
        ga_client, self._params['ga_property_id'])
    self.log_info(f'Fetched #{len(audiences)} audiences from the GA4 Property')
    operations = ga_utils.get_audience_operations_ga4(patches, audiences)
    self.log_info(f'Executing #{len(operations)} operations to update the '
                  f'state of GA4 with the audience configs from your BigQuery')
    ga_utils.run_audience_operations_ga4(
        ga_client,
        self._params['ga_property_id'],
        operations,
        progress_callback=self.log_info)
