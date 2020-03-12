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

import { FormGroup, FormArray, FormBuilder, Validators } from '@angular/forms';
import { Component, OnInit, Input, SimpleChanges, SimpleChange, HostBinding } from '@angular/core';

import { Param } from 'app/models/param';
import { WorkersService } from 'app/jobs/shared/workers.service';

@Component({
  selector: 'app-worker-params',
  templateUrl: './worker-params.component.html',
  styleUrls: ['./worker-params.component.sass']
})
export class WorkerParamsComponent implements OnInit {
  @Input() jobForm: FormGroup;
  private cacheWorkerParams: Object = {};

  sql_editor_options: any = {
    maxLines: 40,
    printMargin: true,
    wrap: true,
    minLines: 5
  };

  constructor(
    private _fb: FormBuilder,
    private workersService: WorkersService
  ) { }

  ngOnInit() {
  }

  @Input()
  set worker_class(worker_class: string) {
    this.workerLoadParams(worker_class);
  }

  get paramsLairs(): FormArray {
    return this.jobForm.get('paramsLairs') as FormArray;
  };

  workerLoadParams(worker_class) {
    if (!worker_class) { return; }
    if (!Object.keys(this.cacheWorkerParams).includes(worker_class)) {
      this.cacheWorkerParams[worker_class] = [];
      this.workersService.getParamsForWorkerClass(worker_class)
                      .then(data => this.jobParamsMapping(data, worker_class));
    } else if (this.cacheWorkerParams[worker_class].length) {
      this.jobParamsMapping(this.cacheWorkerParams[worker_class], worker_class);
    }
  }

  setParamsLairs(params: Param[]) {
    const param_fgs = params.map(param => {
      const validations = [];
      if (param.required && param.type !== 'boolean') {
        validations.push(Validators.required);
      }
      return this._fb.group({
        name: param.name,
        type: param.type,
        label: param.label,
        required: param.required,
        value: [param.value, validations]
      });
    });
    this.jobForm.setControl('paramsLairs', this._fb.array(param_fgs));
  }

  jobParamsMapping(worker_params, worker_class) {
    if (!this.cacheWorkerParams[worker_class].length) {
      for (const worker_param of worker_params) {
        const param = this.jobForm.get('paramsLairs').value.find(p => p.name === worker_param.name);
        if (param) {
          worker_param.value = param.value;
        } else {
          if (worker_param.type === 'boolean') {
            worker_param.value = worker_param.default === 'True';
          } else {
            if (worker_param.default !== undefined) {
              worker_param.value = worker_param.default;
            } else {
              worker_param.value = '';
            }
          }
        }
      }
    }
    this.setParamsLairs(worker_params);
    this.cacheWorkerParams[worker_class] = worker_params;
  }
}
