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

import os
from setuptools import find_packages
from setuptools import setup

PROJECT_DIR = os.path.join(os.path.dirname(__file__), '../')
version_filepath = os.path.join(PROJECT_DIR, 'backend/VERSION')
version = open(version_filepath, 'r').read().strip()

test_deps = [
    'absl-py==1.0.0',
    'pytest==7.1.2',
    'pytest-cov==3.0.0',
]
extras = {
    'test': test_deps,
}

setup(
    name='crmint',
    version=version,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click==8.0.4',
        'pyyaml==6.0',
        'requests==2.24.0',
    ],
    tests_require=test_deps,
    extras_require=extras,
    entry_points="""
        [console_scripts]
        crmint=appcli:entry_point
    """,
)
