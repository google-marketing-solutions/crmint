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
from typing import Iterable, Sequence

from google.cloud import storage


def get_matching_blobs(client: storage.Client,
                       uri_patterns: Iterable[str]) -> Sequence[storage.Blob]:
  """Returns a list of Blob from matching uri patterns on GCS.

  Args:
    client: An instance of `google.cloud.storage.Client`.
    uri_patterns: Iterable of strings representing GCS paths, can contain
        a wildcard to match multiple files.
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
  return blobs


def get_matched_uris(client: storage.Client,
                     uri_patterns: Iterable[str]) -> Sequence[str]:
  """Matches blob uris from given GCS uri patterns.

  Args:
    client: An instance of `google.cloud.storage.Client`.
    uri_patterns: Iterable of strings representing GCS paths, can contain
        a wildcard to match multiple files.

  Returns:
    List of strings of GCS matching blobs uris.
  """
  blobs = get_matching_blobs(client, uri_patterns)
  return [f'gs://{b.bucket.name}/{b.name}' for b in blobs]


def download_file(client: storage.Client,
                  *,
                  uri_path: str,
                  destination_path: str) -> None:
  """Downloads a file from GCS on disk at a given destination path.

  Args:
    client: An instance of `google.cloud.storage.Client`.
    uri_path: Path to the Google Cloud Storage file to download.
    destination_path: Destination path on disk to store the downloaded content.

  Raises:
    ValueError: if the file cannot be found on GCS.
  """
  uri_path = uri_path.removeprefix('gs://')
  bucket_name, blob_name = uri_path.split('/', 1)
  bucket = client.bucket(bucket_name)
  source_blob = bucket.get_blob(blob_name)
  if source_blob is None:
    raise ValueError(f'Blob not found for uri: {uri_path}')
  source_blob.download_to_filename(destination_path)
