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

import { Component, OnInit, Input } from '@angular/core';
import { FormGroup, FormArray, FormBuilder, Validators } from '@angular/forms';

@Component({
  selector: 'app-pipeline-params',
  templateUrl: './pipeline-params.component.html',
  styleUrls: ['./pipeline-params.component.sass']
})
export class PipelineParamsComponent implements OnInit {
  @Input() pipelineForm: FormGroup;
  paramTypes = [
    'string'
  ];

  constructor(
    private _fb: FormBuilder
    ) { }

  ngOnInit() {
  }

  get paramsLairs(): FormArray {
    return this.pipelineForm.get('paramsLairs') as FormArray;
  };

  initParam() {
      return this._fb.group({
        name: ['', [Validators.required, Validators.pattern('[a-zA-Z_][a-zA-Z0-9_]*')]],
        type: ['text'],
        value: ['']
      });
  }

  addParam() {
    const control = <FormArray>this.pipelineForm.controls['paramsLairs'];
    control.push(this.initParam());
  }

  removeParam(i) {
    const control = <FormArray>this.pipelineForm.controls['paramsLairs'];
    control.removeAt(i);
  }
}
