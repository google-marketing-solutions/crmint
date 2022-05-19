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

"""Utilities for storage workers."""

import collections
import fnmatch
from typing import Iterable

from google.cloud import storage


def get_matched_uris(client: storage.Client,
                     uri_patterns: Iterable[str]) -> Iterable[str]:
  """Matches blob uris from given GCS uri patterns.

  Args:
    client: An instance of `google.cloud.storage.Client`.
    uri_patterns: Iterable of strings representing GCS paths, can contain
        a wildcard to match multiple files.

  Returns:
    List of strings of GCS matching blobs uris.
  """
  bucket_to_pattern_map = collections.defaultdict(list)
  for pattern in uri_patterns:
    pattern = pattern.removeprefix('gs://')
    bucket_name, blob_name_pattern = pattern.split('/', 1)
    bucket_to_pattern_map[bucket_name].append(blob_name_pattern)

  blobs = []
  for bucket_name in bucket_to_pattern_map:
    bucket = storage.Bucket(client, bucket_name)
    for blob in client.list_blobs(bucket):
      for blob_name_pattern in bucket_to_pattern_map[bucket_name]:
        if fnmatch.fnmatch(blob.name, blob_name_pattern):
          blobs.append(blob)
          break
  return [f'gs://{b.bucket}/{b.name}' for b in blobs]
