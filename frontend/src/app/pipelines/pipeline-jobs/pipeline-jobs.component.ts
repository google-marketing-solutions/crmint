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

import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { Job } from 'app/models/job';
import { Pipeline } from 'app/models/pipeline';

@Component({
  selector: 'app-pipeline-jobs',
  templateUrl: './pipeline-jobs.component.html',
  styleUrls: ['./pipeline-jobs.component.css']
})
export class PipelineJobsComponent implements OnInit {
  @Input() jobs: Job[] = [];
  @Input() pipeline: Pipeline;
  @Output() jobStartClicked: EventEmitter<string> = new EventEmitter();
  @Output() deleteClicked: EventEmitter<string> = new EventEmitter();

  constructor() { }

  ngOnInit() {}
}
