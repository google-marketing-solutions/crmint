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

import { plainToClass } from 'class-transformer';
import { Router, ActivatedRoute } from '@angular/router';
import { Component, OnInit, Input, HostBinding } from '@angular/core';

import { PipelinesService } from 'app/pipelines/shared/pipelines.service';
import { Pipeline } from 'app/models/pipeline';
import { Job } from 'app/models/job';
import { Log } from 'app/models/log';
import { WorkersService } from 'app/jobs/shared/workers.service';

@Component({
  selector: 'app-pipeline-logs',
  templateUrl: './pipeline-logs.component.html',
  styleUrls: ['./pipeline-logs.component.sass'],
})
export class PipelineLogsComponent implements OnInit {
  @Input() pipeline: Pipeline;
  @Input() jobs: Job[];
  @HostBinding('class') role = 'app-pipeline-logs';
  state = 'pending';
  btnState = 'pending';
  btnNewestState = 'pending';
  logs = [];
  icon = 'error';
  worker_classes = [];
  log_levels = [
    'INFO',
    'WARNING',
    'ERROR'
  ];
  filters = Object.create({
    log_level: null,
    worker_class: null,
    job_id: null,
    query: null,
    next_page_token: null,
    fromdate: null,
    todate: null
  });

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private pipelinesService: PipelinesService,
    private workersService: WorkersService) { }

  ngOnInit() {
  }

  loadLogs() {
    if (this.btnState === 'loading') {
      return;
    }
    this.btnState = 'loading';
    const promise1 = this.pipelinesService.getLogs(this.pipeline.id, this.getFilters())
                                          .then(logs => {
                                            if (!this.logs.length || logs.next_page_token !== this.filters.next_page_token) {
                                              const temp_logs = plainToClass(Log, this.logs.concat(logs.entries) as Log[]);
                                              this.logs = this.removeDuplicates(temp_logs, 'timestamp');
                                              this.filters.next_page_token = logs.next_page_token;
                                            }
                                          });
    const promise2 = this.workersService.getWorkers().then(data => this.worker_classes = data);
    Promise.all([promise1, promise2]).then(() => {
      this.state = 'loaded';
      this.btnState = 'pending';
    }).catch(reason => {
      console.error('reason', reason);
      this.state = 'error';
      this.btnState = 'pending';
    });
  }

  loadNewestLogs(filterLoading = false) {
    if (this.btnNewestState === 'loading' && !filterLoading) {
      return;
    }
    this.btnNewestState = 'loading';
    this.filters.next_page_token = null;
    const promise1 = this.pipelinesService.getLogs(this.pipeline.id, this.getFilters())
                                          .then(logs => {
                                            if (filterLoading) {
                                              this.logs = plainToClass(Log, logs.entries as Log[]);
                                            } else {
                                              const temp_logs = plainToClass(Log, logs.entries.concat(this.logs) as Log[]);
                                              this.logs = this.removeDuplicates(temp_logs, 'timestamp');
                                            }
                                            this.filters.next_page_token = logs.next_page_token;
                                          });
    Promise.all([promise1]).then(() => {
      this.state = 'loaded';
      this.btnNewestState = 'pending';
    }).catch(reason => {
      console.error('reason', reason);
      this.state = 'error';
      this.btnNewestState = 'pending';
    });
  }

  removeDuplicates(array, prop) {
    return array.filter((obj, pos, arr) => {
      return arr.map(mapObj => mapObj[prop]).indexOf(obj[prop]) === pos;
    });
  }

  getFilters() {
    const filters = Object.assign({}, this.filters);
    for (const propName in filters) {
      if (filters[propName] === null || filters[propName] === undefined) {
        delete filters[propName];
      }
    }
    if (filters.fromdate) {
      filters.fromdate = filters.fromdate.toISOString();
    }
    if (filters.todate) {
      filters.todate = filters.todate.toISOString();
    }
    return filters;
  }

  btnText() {
    return this.btnState === 'pending' ? 'Load more' : 'Loading...';
  }

  btnNewestText() {
    return this.btnNewestState === 'pending' ? 'Load newest' : 'Loading...';
  }

}
