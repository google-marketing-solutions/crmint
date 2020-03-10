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

import { Component, OnInit } from '@angular/core';
import { FormGroup, FormBuilder, Validators, FormArray } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';

import { PipelinesService } from './../shared/pipelines.service';
import { Pipeline } from 'app/models/pipeline';
import { Schedule } from 'app/models/schedule';
import { Param } from 'app/models/param';

@Component({
  selector: 'app-pipeline-form',
  templateUrl: './pipeline-form.component.html',
  styleUrls: ['./pipeline-form.component.sass']
})
export class PipelineFormComponent implements OnInit {

  pipelineForm: FormGroup;
  pipeline: Pipeline = new Pipeline();
  state = 'loading'; // State has one of values: loading, loaded or error
  title = 'New Pipeline';
  error_message = '';

  constructor(
    private _fb: FormBuilder,
    private pipelinesService: PipelinesService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.title = this.router.url.endsWith('new') ? 'New Pipeline' : 'Edit Pipeline';
    this.createForm();
  }

  createForm() {
    this.pipelineForm = this._fb.group({
      name: ['', Validators.required],
      emails_for_notifications: [''],
      run_on_schedule: [false],
      schedulesLairs: this._fb.array([]),
      paramsLairs: this._fb.array([]),
    });
  }

  assignModelToForm() {
    this.pipelineForm.reset({
      name: this.pipeline.name,
      emails_for_notifications: this.pipeline.emails_for_notifications,
      run_on_schedule: this.pipeline.run_on_schedule,
      paramsLairs: this._fb.array([])
    });
    this.setSchedules(this.pipeline.schedules);
    this.setParamsLairs(this.pipeline.params);
  }

  setSchedules(schedules: Schedule[]) {
    const schedule_fgs = schedules.map(schedule => this._fb.group(schedule));
    this.pipelineForm.setControl('schedulesLairs', this._fb.array(schedule_fgs));
  }

  setParamsLairs(params: Param[]) {
    const param_fgs = params.map(param => this._fb.group(param));
    this.pipelineForm.setControl('paramsLairs', this._fb.array(param_fgs));
  }

  get schedulesLairs(): FormArray {
    return this.pipelineForm.get('schedulesLairs') as FormArray;
  }

  removeSchedule(i) {
    const control = <FormArray>this.pipelineForm.controls['schedulesLairs'];
    control.removeAt(i);
  }

  initSchedule() {
      return this._fb.group({
          cron: [''],
      });
  }

  addSchedule() {
    const control = <FormArray>this.pipelineForm.controls['schedulesLairs'];
    control.push(this.initSchedule());
  }

  ngOnInit() {
    this.route.params.subscribe(params => {
      const id = params['id'];

      if (!id) {
        this.state = 'loaded';
        return;
      }

      this.pipelinesService.getPipeline(id)
          .then(pipeline => {
            this.pipeline = pipeline as Pipeline;
            this.state = 'loaded';
            this.assignModelToForm();
          })
          .catch(response => {
            if (response.status === 404) {
              this.router.navigate(['pipelines']);
            } else {
              this.state = 'error';
            }
          });
    });
  }

  prepareSavePipeline() {
    const formModel = this.pipelineForm.value;

    // deep copy of form model lairs
    const schedulesDeepCopy: Schedule[] = formModel.schedulesLairs.map(
      (schedule: Schedule) => Object.assign({}, schedule)
    );

    // deep copy of form model lairs
    const paramsDeepCopy: Param[] = formModel.paramsLairs.map(
      (param: Param) => Object.assign({}, param)
    );

    // return new `Pipeline` object containing a combination of original pipeline value(s)
    // and deep copies of changed form model values
    this.pipeline.name = formModel.name as string;
    this.pipeline.run_on_schedule = formModel.run_on_schedule as boolean;
    this.pipeline.emails_for_notifications = formModel.emails_for_notifications as string;
    this.pipeline.schedules = schedulesDeepCopy;
    this.pipeline.params = paramsDeepCopy;
  }

  save() {
    this.prepareSavePipeline();

    if (this.pipeline.id) {
      this.pipelinesService.updatePipeline(this.pipeline)
        .then(() => {
          this.router.navigate(['pipelines', this.pipeline.id]);
          this.error_message = '';
        }).catch(response => {
          this.error_message = response || 'An error occurred';
        });
    } else {
      this.pipelinesService.addPipeline(this.pipeline)
        .then(() => this.router.navigate(['pipelines']));
    }
  }

  cancel() {
    if (this.pipeline.id) {
      this.router.navigate(['pipelines', this.pipeline.id]);
    } else {
      this.router.navigate(['pipelines']);
    }
  }
}
