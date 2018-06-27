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

import { SharedModule } from 'app/shared/shared.module';
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';

import { ClickOutsideModule } from 'ng-click-outside';
import { PrettycronPipe } from 'app/pipes/prettycron.pipe';

import { PipelinesComponent } from './pipelines.component';
import { PipelineFormComponent } from './pipeline-form/pipeline-form.component';
import { PipelinesService } from './shared/pipelines.service';
import { PipelineViewComponent } from './pipeline-view/pipeline-view.component';
import { PipelineParamsComponent } from './pipeline-form/pipeline-params/pipeline-params.component';
import { PipelineJobsComponent } from './pipeline-jobs/pipeline-jobs.component';
import { PipelineGraphComponent } from './pipeline-graph/pipeline-graph.component';
import { PipelineLogsComponent } from './pipeline-logs/pipeline-logs.component';

@NgModule({
  imports: [
    SharedModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    ClickOutsideModule
  ],
  declarations: [
    PipelinesComponent,
    PipelineFormComponent,
    PipelineViewComponent,
    PipelineParamsComponent,
    PrettycronPipe,
    PipelineGraphComponent,
    PipelineJobsComponent,
    PipelineLogsComponent,
],
  exports: [
    PipelinesComponent
  ],
  providers: [
    PipelinesService
  ]
})
export class PipelinesModule { }
