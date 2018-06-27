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

import { Router, ActivatedRoute } from '@angular/router';
import { Component, OnInit, Input, ElementRef, EventEmitter, Output, AfterViewInit, OnDestroy } from '@angular/core';

import { Pipeline } from 'app/models/pipeline';
import { Job } from 'app/models/job';
import { PipelineGraphDrawer } from './pipeline-graph-drawer';

@Component({
  selector: 'app-pipeline-graph',
  templateUrl: './pipeline-graph.component.html',
  styleUrls: ['./pipeline-graph.component.sass']
})
export class PipelineGraphComponent implements OnInit, AfterViewInit, OnDestroy {
  @Output() deleteClicked: EventEmitter<string> = new EventEmitter();
  @Output() jobStartClicked: EventEmitter<string> = new EventEmitter();

  @Input() pipeline: Pipeline;
  @Input() jobs: Job[];

  pgdrawer: PipelineGraphDrawer;

  constructor(
    private element: ElementRef,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {}

  ngAfterViewInit() {
    this.pgdrawer = new PipelineGraphDrawer(this);
  }

  ngOnDestroy() {
    this.pgdrawer.destroy();
  }

  redraw() {
    this.pgdrawer.redraw();
  }

  onJobStart(job: Job) {
    this.jobStartClicked.emit(String(job.id));
  }

  onJobEdit(job: Job) {
    this.router.navigate(['jobs', job.id, 'edit']);
  }

  onJobRemove(job: Job) {
    this.deleteClicked.emit(String(job.id));
  }

  onClickedOutside(e: Event) {
    this.pgdrawer.clickOutside();
  }
}
