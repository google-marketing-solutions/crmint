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

import { Component, OnInit, HostBinding, Input } from '@angular/core';
import { plainToClass } from 'class-transformer';

import { Stage } from 'app/models/stage';
import { StagesService } from '../shared/stages.service';

@Component({
  selector: 'app-stages',
  templateUrl: './stages.component.html',
  styleUrls: ['./stages.component.sass']
})
export class StagesComponent implements OnInit {

  @Input() stages: Stage[] = [];
  state = 'loading'; // State has one of values: loading, loaded, error
  newStageName = '';

  constructor(
    private stagesService: StagesService
  ) { }

  ngOnInit() {
  }

  addStage() {
    if (this.newStageName === '') {
      return;
    }
    this.stagesService.addStage({ sid: this.newStageName })
                      .then(data => {
                        this.stages.push(plainToClass(Stage, data as Stage));
                      });

    this.newStageName = '';
  }

  deleteStage(stage) {
    const index = this.stages.indexOf(stage);
    this.stages.splice(index, 1);
    this.stagesService.deleteStage(stage.id);
  }

}
