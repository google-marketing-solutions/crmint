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

import { Router, ActivatedRoute } from '@angular/router';
import { Component, OnInit } from '@angular/core';
import { plainToClass } from 'class-transformer';

import { MlModelsService } from '../shared/ml-models.service';
import { Pipeline } from 'app/models/pipeline';
import { MlModel } from 'app/models/ml-model';

@Component({
  selector: 'app-ml-model-view',
  templateUrl: './ml-model-view.component.html',
  styleUrls: ['./ml-model-view.component.sass'],
})
export class MlModelViewComponent implements OnInit {
  mlModel: MlModel = new MlModel();
  state = 'loading'; // State has one of values: loading, loaded, error
  tab = 0;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private mlModelsService: MlModelsService) {}

  ngOnInit() {
    this.route.params.subscribe(params => {
      const id = params['id'];

      if (!id) {
        this.router.navigate(['ml-models']);
      }

      this.mlModelsService.get(id)
        .then(mlModel => {
          console.log(mlModel)
          this.mlModel = plainToClass(MlModel, mlModel as MlModel);
          if (this.mlModel.pipelines.length > 0) {
            this.mlModel.pipelines = plainToClass(Pipeline, mlModel.pipelines as Pipeline[])
          }
          this.state = 'loaded';
        })
        .catch(e => {
          if (e.status === 404) {
            this.router.navigate(['ml-models']);
          }
          return Promise.reject(true);
        });
    });
  }

  extractSetupSql(pipeline: Pipeline) {
    if (pipeline) {
      const job = pipeline.jobs.find(job => job.name.endsWith('Setup'));
      const param = job.params.find(param => param.name === 'script');
      return param.value;
    } else {
      return '';
    }
  }

  deletePipeline(pipeline: Pipeline) {

  }

  setTab(index: number) {
    this.tab = index;
  }
}
