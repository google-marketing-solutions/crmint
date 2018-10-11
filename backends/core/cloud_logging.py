# Copyright 2018 Google Inc
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

from google.cloud.logging import Client

from core.app_data import SA_DATA, SA_FILE


if SA_DATA.get('private_key', ''):
  client = Client.from_service_account_json(SA_FILE)
else:
  client = Client()


logger_name = 'crmintapplogger'
logger = client.logger(logger_name)
