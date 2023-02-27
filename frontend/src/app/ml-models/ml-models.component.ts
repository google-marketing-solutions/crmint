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

import { Component, OnInit, Inject, forwardRef, Pipe } from '@angular/core';

import { plainToClass } from 'class-transformer';

import { MlModel } from 'app/models/ml-model';
import { Pipeline } from 'app/models/pipeline';
import { MlModelsService } from './shared/ml-models.service';
import { AppComponent } from 'app/app.component';

@Component({
  selector: 'app-ml-models',
  templateUrl: './ml-models.component.html',
  styleUrls: ['./ml-models.component.sass']
})
export class MlModelsComponent implements OnInit {

  mlModels: MlModel[] = [];
  state: string = 'loading'; // State has one of values: loading, loaded, error
  expanded = {};

  constructor(
    private mlModelsService: MlModelsService,
    @Inject(forwardRef(() => AppComponent)) private appComponent: AppComponent
  ) { }

  ngOnInit() {
    this.mlModelsService.getAll()
      .then(data => {
        this.mlModels = plainToClass(MlModel, data as MlModel[]);
        for (const mlModel of this.mlModels) {
          mlModel.pipelines = plainToClass(Pipeline, mlModel.pipelines as Pipeline[])
        }
        this.state = 'loaded';
      })
      .catch(() => this.state = 'error');
  }

  deleteModel(mlModel: MlModel) {
    if (confirm(`Are you sure you want to delete ${mlModel.name}?`)) {
      for (const pipeline of mlModel.pipelines) {
        if (pipeline.blocked_managing()) {
          this.appComponent.addAlert('Cannot delete model while associated pipeline is active or scheduled.');
        }
      }
      const index = this.mlModels.indexOf(mlModel);
      this.mlModels.splice(index, 1);

      this.mlModelsService.delete(mlModel.id)
          .catch(err => {
            console.log('error', err);
            const defaultMessage = 'Could not delete model.';
            let message;
            try {
              message = JSON.parse(err._body).message || defaultMessage;
            } catch (e) {
              message = defaultMessage;
            }

            this.appComponent.addAlert(message);
            // Revert the view back to its original state
            this.mlModels.splice(index, 0, mlModel);
          });
    }
  }
}
