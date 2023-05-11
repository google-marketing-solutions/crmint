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

import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { MlModelsComponent } from './ml-models.component';
import { MlModelFormComponent } from './ml-model-form/ml-model-form.component';
import { MlModelViewComponent } from './ml-model-view/ml-model-view.component';

const routes: Routes = [
  {
    path: 'ml-models',
    component: MlModelsComponent,
    pathMatch: 'full'
  },
  {
    path: 'ml-models/new',
    component: MlModelFormComponent
  },
  {
    path: 'ml-models/:id/edit',
    component: MlModelFormComponent
  },
  {
    path: 'ml-models/:id',
    component: MlModelViewComponent,
    pathMatch: 'full'
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class MlModelsRoutingModule { };
