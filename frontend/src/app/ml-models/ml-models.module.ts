// Copyright 2023 Google Inc
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

import { MlModelsComponent } from './ml-models.component';
import { MlModelsService } from './shared/ml-models.service';
import { MlModelFormComponent } from './ml-model-form/ml-model-form.component';
import { MlModelViewComponent } from './ml-model-view/ml-model-view.component';

@NgModule({
  imports: [
    SharedModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule
  ],
  declarations: [
    MlModelsComponent,
    MlModelFormComponent,
    MlModelViewComponent
],
  exports: [
    MlModelsComponent
  ],
  providers: [
    MlModelsService
  ]
})
export class MlModelsModule { }
