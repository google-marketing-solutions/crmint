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

import run_ibackend
from core.models import GeneralSetting

# SETUP SETTINGS
SETTINGS = ['emails_for_notifications']
for setting in SETTINGS:
  gsetting = GeneralSetting.where(name=setting).first()
  if not gsetting:
    gsetting = GeneralSetting()
    gsetting.name = setting
    gsetting.save()
    print 'Added setting', setting
