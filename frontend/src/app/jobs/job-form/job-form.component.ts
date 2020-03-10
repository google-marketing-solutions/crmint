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

import { Component, OnInit, OnChanges } from '@angular/core';
import { FormGroup, FormBuilder, Validators, FormArray } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';


import { Job, StartCondition } from 'app/models/job';
import { Param } from 'app/models/param';
import { JobsService } from './../shared/jobs.service';
import { WorkersService } from './../shared/workers.service';
import { PipelinesService } from 'app/pipelines/shared/pipelines.service';
import { Pipeline } from 'app/models/pipeline';

@Component({
  selector: 'app-job-form',
  templateUrl: './job-form.component.html',
  styleUrls: ['./job-form.component.sass']
})
export class JobFormComponent implements OnInit {

  jobForm: FormGroup;
  job: Job = new Job();
  pipeline: Pipeline;
  worker_classes = [];
  conditions = [
    'success',
    'fail',
    'whatever'
  ];
  state = 'loading'; // State has one of values: loading, loaded, error
  title = 'New Job';
  error_message = '';

  dependency_jobs = [];

  initStartCondition() {
      return this._fb.group({
          preceding_job_id: [''],
          condition: ['']
      });
  }

  getDependencyJobs() {
    const promise1 = this.pipelinesService.getPipeline(this.job.pipeline_id)
                                     .then(data => {
                                       this.pipeline = data as Pipeline;
                                     });

    const promise2 = this.jobsService.getJobsByPipeline(this.job.pipeline_id)
                    .then(data => {
                      this.dependency_jobs = data.filter(job => job.id !== this.job.id)
                                                 .map(job => [job.name, job.id]);
                    });

    const promise3 = this.workersService.getWorkers().then(data => {
      this.worker_classes = data;
    });

    Promise.all([promise1, promise2, promise3]).then(results => {
      this.state = 'loaded';
    }).catch(reason => {
      this.state = 'error';
    });
  }

  constructor(
    private _fb: FormBuilder,
    private jobsService: JobsService,
    private workersService: WorkersService,
    private pipelinesService: PipelinesService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.title = this.router.url.search('/new') !== -1 ? 'New Job' : 'Edit Job';
    this.createForm();
  }

  createForm() {
    this.jobForm = this._fb.group({
      name: ['', Validators.required],
      worker_class: ['', Validators.required],
      startConditionsLairs: this._fb.array([]),
      paramsLairs: this._fb.array([])
    });
  }

  assignModelToForm() {
    this.jobForm.reset({
      name: this.job.name,
      worker_class: this.job.worker_class,
    });
    this.setStartConditions(this.job.start_conditions);
    this.setParamsLairs(this.job.params);
  }

  setStartConditions(start_conditions: StartCondition[]) {
    const start_condition_fgs = start_conditions.map(start_condition => this._fb.group(start_condition));
    this.jobForm.setControl('startConditionsLairs', this._fb.array(start_condition_fgs));
  }

  setParamsLairs(params: Param[]) {
    const param_fgs = params.map(param => this._fb.group(param));
    this.jobForm.setControl('paramsLairs', this._fb.array(param_fgs));
  }

  get startConditionsLairs(): FormArray {
    return this.jobForm.get('startConditionsLairs') as FormArray;
  };

  ngOnInit() {
    this.route.params.subscribe(params => {
      const id = params['id'];

      if (!id) {
        this.route.queryParams.subscribe(queryParams => {
          this.job.pipeline_id = queryParams['pipeline_id'];
          this.getDependencyJobs();
        });
        return;
      }

      this.jobsService.getJob(id)
          .then(
            job => {
              this.job = job as Job;
              this.getDependencyJobs();
              this.assignModelToForm();
            },
            response => {
              if (response.status === 404) {
                this.router.navigate(['jobs']);
              } else {
                this.state = 'error';
              }
            });
    });
  }

  addStartCondition() {
    const control = <FormArray>this.jobForm.controls['startConditionsLairs'];
    control.push(this.initStartCondition());
  }

  removeStartCondition(i) {
    const control = <FormArray>this.jobForm.controls['startConditionsLairs'];
    control.removeAt(i);
  }

  prepareSaveJob() {
    const formModel = this.jobForm.value;

    // deep copy of form model lairs
    const startConditionsDeepCopy: StartCondition[] = formModel.startConditionsLairs.map(
      (startCondition: StartCondition) => Object.assign({}, startCondition)
    );

    // deep copy of form model lairs
    const paramsDeepCopy: Param[] = formModel.paramsLairs.map(
      (param: Param) => Object.assign({}, param)
    );
    // return new `Job` object containing a combination of original job value(s)
    // and deep copies of changed form model values
    this.job.name = formModel.name as string;
    this.job.worker_class = formModel.worker_class as string;
    this.job.start_conditions = startConditionsDeepCopy;
    this.job.params = paramsDeepCopy;
  }

  save() {
    let result;
    this.prepareSaveJob();

    if (this.job.id) {
      result = this.jobsService.updateJob(this.job);
    } else {
      result = this.jobsService.addJob(this.job);
    }

    result.then(() => {
      this.router.navigate(['pipelines', this.job.pipeline_id]);
      this.error_message = '';
    }).catch(response => {
      this.error_message = response || 'An error occurred';
    });
  }

  cancel() {
    this.router.navigate(['pipelines', this.job.pipeline_id]);
  }

}
