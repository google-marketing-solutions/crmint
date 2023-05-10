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

"""CRMint's abstract worker for dealing with BigQuery in a batch mode."""

import abc
from typing import Tuple

from google.api_core import page_iterator

from jobs.workers.bigquery import bq_worker


# Param name to use when passing around a BQ table name to process between
# workers and sub-workers.
BQ_TABLE_TO_PROCESS_PARAM = 'bq_table_to_process'

# Param name to use when passing around a BQ page token between workers
# and sub-workers
BQ_PAGE_TOKEN_PARAM = 'bq_page_token'

# Param name to use when passing around batch size between workers and
# sub-workers.
BQ_BATCH_SIZE_PARAM = 'bq_batch_size'


class BQBatchDataWorker(bq_worker.BQWorker, abc.ABC):
  """Abstract worker for batching data into manageable chunks.

  This worker will start the processing of a large dataset from BQ, enqueueing
  a sub-worker to handle each chunk of data pulled from the BQ table.  If the
  original instance enqueues too many sub-workers, it will enqueue another
  instance of itself and stop processing.

  In order to use this batch processing, an implementer needs to do the
  following:
    1)  Create an implementation of the 'TablePageResultsProcessorWorker'
        sub-worker to handle processing each page of data.
    2)  Create an implementation of this base class with the
        'get_sub_worker_name' function, so the base worker knows which
        sub-worker to enqueue.
    3)  Add the sub-worker class name to the sub-workers private workers
        mapping.
    4)  Add the base class to the public workers mapping.
  """

  # BigQuery batch size for querying results.
  DEFAULT_BQ_BATCH_SIZE = 1000

  # Maximum number of jobs to enqueued before spawning a new scheduler.
  MAX_ENQUEUED_JOBS_PER_COORDINATOR = 50

  def _execute(self) -> None:
    table_name_to_process = self._params.get(BQ_TABLE_TO_PROCESS_PARAM, None)
    if not table_name_to_process:
      raise ValueError('Param \'' + BQ_TABLE_TO_PROCESS_PARAM +
                       '\' needs to be set for batch processing.')

    page_token = self._params.get(BQ_PAGE_TOKEN_PARAM, None)
    client = self._get_client()
    row_iterator = client.list_rows(
      table=client.get_table(table_name_to_process),
      page_token=page_token,
      page_size=self.DEFAULT_BQ_BATCH_SIZE
    )

    enqueued_jobs_count = 0
    for _ in row_iterator.pages:
      # Enqueue job for this page
      worker_params = self._params.copy()
      worker_params[BQ_PAGE_TOKEN_PARAM] = page_token
      worker_params[BQ_BATCH_SIZE_PARAM] = self.DEFAULT_BQ_BATCH_SIZE

      self._enqueue(
        self._get_sub_worker_name(),
        worker_params
      )
      enqueued_jobs_count += 1

      # Updates the page token reference for the next iteration.
      page_token = row_iterator.next_page_token

      # Spawns a new job to schedule the remaining pages.
      if (enqueued_jobs_count >= self.MAX_ENQUEUED_JOBS_PER_COORDINATOR
        and page_token is not None):
        worker_params = self._params.copy()
        worker_params[BQ_PAGE_TOKEN_PARAM] = page_token
        self._enqueue(self.__class__.__name__, worker_params)
        return

  @abc.abstractmethod
  def _get_sub_worker_name(self) -> str:
    """Abstract function that returns the name of the sub-worker to enqueue."""


class TablePageResultsProcessorWorker(bq_worker.BQWorker, abc.ABC):
  """Abstract sub-worker for processing a page of results from a BQ table.

  This walker specializes in handling large BQ data sets, by processing a
  page's worth of data from BQ.  The size of the page is determined by 2
  configuration parameters:  'bq_page_token' and 'bq_batch_size'.

  Concrete implementations need to implement the _process_page_results
  function, since that function will be called by the processing
  _execute function.
  """
  def _extract_parameters(self) -> Tuple[str, str, int]:
    page_token = self._params.get('bq_page_token', None)
    if not page_token:
      raise ValueError('Param \'' + BQ_PAGE_TOKEN_PARAM + '\' needs to be set'
                       ' for batch processing.')

    table_name_to_process = self._params.get(BQ_TABLE_TO_PROCESS_PARAM, None)
    if not table_name_to_process:
      raise ValueError('Param \'' + BQ_TABLE_TO_PROCESS_PARAM +
                       '\' needs to be set for batch processing.')

    batch_size = self._params.get(BQ_BATCH_SIZE_PARAM, None)
    if not batch_size:
      raise ValueError('Param \'' + BQ_BATCH_SIZE_PARAM + '\' needs to be set'
                       ' for batch processing.')

    return table_name_to_process, page_token, batch_size

  def _execute(self) -> None:
    """Process the chunk of BQ data."""
    (table_name_to_process, page_token, batch_size) = self._extract_parameters()

    client = self._get_client()
    table = client.get_table(table_name_to_process)

    row_iterator = client.list_rows(
      table=table,
      page_token=page_token,
      page_size=batch_size)

    # We are only interested in the first page results, since our chunk is
    # fully specified by (page_token, batch_size). The next page will be
    # processed by another processing instance.
    first_page = next(row_iterator.pages)
    self._process_page_results(first_page)

  @abc.abstractmethod
  def _process_page_results(self, page_data: page_iterator.Page) -> None:
    """Abstract method for processing the page data pulled from BQ.

    Implementations of this function will be called, and this is were the
    work of processing the data occurs (ie, pushing data from BQ up to a
    Google API).
    """
