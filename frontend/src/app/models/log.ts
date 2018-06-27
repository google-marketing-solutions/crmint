// Copyright 2018 Google Inc
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

export class Log {
  id: number;
  job_name: string;
  timestamp: string;
  payload: object;

  log_level(): string {
    return this.payload['log_level'];
  }

  worker_class(): string {
    return this.payload['labels']['worker_class'];
  }

  log_lower_level(): string {
    return this.log_level().toLowerCase();
  }

  icon(): string {
    if (this.log_level() === 'INFO') {
      return 'info';
    }
    return 'error';
  }

  message(): string {
    return ('Job: <strong>' + this.job_name + '</strong>' +
            ', Worker Class: <strong>' + this.worker_class() + '</strong>' +
            '<br/>' +
            this.payload['message'].replace('<', '&lt;'));
  }
}
