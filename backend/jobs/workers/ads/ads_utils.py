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

"""Utilities for Google Ads workers."""
from typing import Dict
from typing import Any
from google.ads.googleads.client import GoogleAdsClient


def get_ads_client_with_service_account(
  service_account_keys_file_path: str
) -> None:
  """Generates a Google Ads client from a service account keys file."""
