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

import subprocess


DATABASE_NAME = "crmintapp"
DATABASE_USER = "crmintapp"


def create_database():
  db_command = "echo \"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8;"\
               "GRANT ALL PRIVILEGES ON {db_user}.* TO '{db_user}'@'localhost' IDENTIFIED BY '{db_user}';" \
               "FLUSH PRIVILEGES;\" | mysql -u root"
  res = subprocess.Popen(
      db_command.format(db_name=DATABASE_NAME, db_user=DATABASE_USER),
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      shell=True)
  error_message = res.communicate()[1]
  if error_message:
    raise Exception(error_message)
