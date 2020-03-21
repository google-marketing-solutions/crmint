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

import { Router, ActivatedRoute } from '@angular/router';
import { Component, OnInit, ViewChild } from '@angular/core';
import { plainToClass } from 'class-transformer';

import { Job } from 'app/models/job';
import { JobsService } from 'app/jobs/shared/jobs.service';
import { PipelinesService } from './../shared/pipelines.service';
import { Pipeline } from 'app/models/pipeline';

@Component({
  selector: 'app-pipeline-view',
  templateUrl: './pipeline-view.component.html',
  styleUrls: ['./pipeline-view.component.sass'],
})
export class PipelineViewComponent implements OnInit {
  @ViewChild('graph', { static: false }) graph;
  @ViewChild('pipelineLogs', { static: false }) pipelineLogs;
  pipeline: Pipeline = new Pipeline();
  jobs: Job[] = [];
  state = 'loading'; // State has one of values: loading, loaded, error
  indexTabActivated = 0;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private pipelinesService: PipelinesService,
    private jobsService: JobsService
  ) { }

  ngOnInit() {
    this.route.params.subscribe(params => {
      const id = params['id'];

      if (!id) { this.router.navigate(['pipelines']); }

      this.loadJobs(id);
    });
  }

  loadJobs(pipeline_id) {
    const promise1 = this.pipelinesService.getPipeline(pipeline_id)
        .then(pipeline => this.pipeline = plainToClass(Pipeline, pipeline as Pipeline))
        .catch(e => {
          if (e.status === 404) {
            this.router.navigate(['pipelines']);
          }
          return Promise.reject(true);
        });

    const promise2 = this.jobsService.getJobsByPipeline(pipeline_id)
                                     .then(data => this.jobs = plainToClass(Job, data as Job[]));

    return Promise.all([promise1, promise2]).then(() => {
      this.state = 'loaded';
      setTimeout(() => {
        this.updateGraph();
        // this.loadLogs();
        this.startAutorefresh();
      }, 100);
    }).catch(reason => {
      console.error('reason', reason);
      if (!this.jobs.length) {
        this.state = 'error';
      }
    });
  }

  deleteJob(job_id) {
    const job = this.jobs.find(obj => obj.id === Number(job_id));
    if (confirm(`Are you sure you want to delete ${job.name}?`)) {
      const index = this.jobs.indexOf(job);
      this.jobs.splice(index, 1);
      this.updateGraph();

      this.jobsService.deleteJob(job.id)
          .then(null,
          () => {
            alert('Could not delete job.');
            // Revert the view back to its original state
            this.jobs.splice(index, 0, job);
            this.updateGraph();
          });
    }
  }

  startJob(job_id) {
    const job = this.jobs.find(obj => obj.id === Number(job_id)) as Job;
    this.jobsService.startJob(job.id)
                    .then(() => {
                      this.loadJobs(this.pipeline.id);
                    });
  }

  startPipeline() {
    this.pipelinesService.startPipeline(this.pipeline.id)
                         .then(data => {
                           this.pipeline = plainToClass(Pipeline, data as Pipeline);
                           this.loadJobs(this.pipeline.id);
                          });
  }

  startAutorefresh() {
    if (!this.pipeline.is_active()) {
      return;
    }
    setTimeout(() => {
      if (this.pipeline.is_active()) {
        this.loadJobs(this.pipeline.id);
      }
    }, 10000);
  }

  stopPipeline() {
    this.pipelinesService.stopPipeline(this.pipeline.id)
                         .then(data => this.pipeline = plainToClass(Pipeline, data as Pipeline));
  }

  export() {
    this.pipelinesService.exportPipeline(this.pipeline.id)
                         .then(res => {
                           const blob = new Blob([JSON.stringify(res.body, null, 2)], { type: 'application/json' });
                           const a = document.getElementById('crmi-download');
                           const url = window.URL.createObjectURL(blob);
                           a.setAttribute('href', url);
                           a.setAttribute('download', res.headers.get('Filename'));
                           a.click();
                           window.URL.revokeObjectURL(url);
                         });
  }

  updateRunOnSchedule(event) {
    this.pipelinesService.updateRunOnSchedule(this.pipeline.id, event.checked)
                         .then(data => {
                           this.pipeline = plainToClass(Pipeline, data as Pipeline);
                           this.updateGraph();
                          });
  }

  tabChange(event) {
    this.indexTabActivated = event.index;
    this.updateGraph();
    this.loadLogs();
  }

  updateGraph() {
    if (this.indexTabActivated === 0 && this.graph) {
      this.graph.redraw();
    }
  }

  loadLogs() {
    if (this.indexTabActivated === 2 && this.pipelineLogs.state !== 'loading') {
      this.pipelineLogs.loadNewestLogs();
    }
  }

}
