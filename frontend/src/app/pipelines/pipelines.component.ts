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

import { Component, OnInit, Inject, forwardRef } from '@angular/core';

import { plainToClass } from 'class-transformer';

import { Pipeline } from 'app/models/pipeline';
import { PipelinesService } from './shared/pipelines.service';
import { AppComponent } from 'app/app.component';

@Component({
  selector: 'app-pipelines',
  templateUrl: './pipelines.component.html',
  styleUrls: ['./pipelines.component.sass']
})
export class PipelinesComponent implements OnInit {

  pipelines: Pipeline[] = [];
  filesToUpload: Array<File> = [];
  state = 'loading'; // State has one of values: loading, loaded, error

  constructor(
    private pipelinesService: PipelinesService,
    @Inject(forwardRef(() => AppComponent)) private appComponent: AppComponent
  ) { }

  ngOnInit() {
    this.pipelinesService.getPipelines()
        .then(data => {
          this.pipelines = plainToClass(Pipeline, data as Pipeline[]);
          this.state = 'loaded';
        }).catch(err => {
          this.state = 'error';
        });
  }

  deletePipeline(pipeline) {
    if (confirm(`Are you sure you want to delete ${pipeline.name}?`)) {
      const index = this.pipelines.indexOf(pipeline);
      this.pipelines.splice(index, 1);

      this.pipelinesService.deletePipeline(pipeline.id)
          .catch(err => {
            console.log('error', err);
            const defaultMessage = 'Could not delete pipeline.';
            let message;
            try {
              message = JSON.parse(err._body).message || defaultMessage;
            } catch (e) {
              message = defaultMessage;
            }

            this.appComponent.addAlert(message);
            // Revert the view back to its original state
            this.pipelines.splice(index, 0, pipeline);
          });
    }
  }

  importPipeline(data) {
    this.pipelinesService.importPipeline(data.target.files[0])
                         .then(pipeline => this.pipelines.push(plainToClass(Pipeline, pipeline as Pipeline)));
  }

}
