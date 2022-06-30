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

import { WorkersService } from 'app/jobs/shared/workers.service';
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { CodemirrorModule } from '@ctrl/ngx-codemirror';

import { SharedModule } from './../shared/shared.module';
import { JobsComponent } from './jobs.component';
import { JobsService } from './shared/jobs.service';
import { JobFormComponent } from './job-form/job-form.component';
import { WorkerParamsComponent } from './job-form/worker-params/worker-params.component';

@NgModule({
  imports: [
    CommonModule,
    SharedModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    CodemirrorModule
  ],
  declarations: [
    JobsComponent,
    JobFormComponent,
    WorkerParamsComponent
],
  exports: [
    JobsComponent
  ],
  providers: [
    JobsService,
    WorkersService
  ]
})
export class JobsModule { }
