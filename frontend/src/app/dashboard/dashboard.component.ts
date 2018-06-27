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

import { Router } from '@angular/router';
import { Component, OnInit } from '@angular/core';
import { plainToClass } from 'class-transformer';

import { StagesService } from './shared/stages.service';
import { Stage } from 'app/models/stage';
import { Pipeline } from 'app/models/pipeline';
import { environment } from 'environments/environment';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.sass']
})
export class DashboardComponent implements OnInit {
  stages: Stage[];
  pipelines: Pipeline[] = [];
  enabled_stages: boolean = environment.enabled_stages;

  stages_state = 'loading';
  pipelines_state = 'loading';

  constructor(
    private stagesService: StagesService,
    private router: Router
  ) { }

  ngOnInit() {
    if (!this.enabled_stages) {
      this.router.navigate(['pipelines']);
    }
    this.loadStages();
  }

  loadStages() {
    this.stagesService.getStages()
                      .then(data => {
                        this.stages = plainToClass(Stage, data as Stage[]);
                        this.stages_state = 'loaded';
                        this.loadPipelines();
                      }).catch(err => {
                        this.stages_state = 'error';
                      });
  }

  loadPipelines() {
    const promises = this.stagesService.getPipelinesForAllStages(this.stages);
    Promise.all(promises).then(results => {
      for (const result of results) {
        this.pipelines = this.pipelines.concat(result);
      }
      this.pipelines_state = 'loaded';
    }).catch(err => {
      console.log('err', err);
      this.pipelines_state = 'error';
    });
  }
}
