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
import { Component, OnInit, Input, ElementRef, EventEmitter, Output, ViewChild } from '@angular/core';

import { Pipeline } from 'app/models/pipeline';
import { Job } from 'app/models/job';
import { PipelineGraph } from './pipeline-graph';

@Component({
  selector: 'app-pipeline-graph',
  templateUrl: './pipeline-graph.component.html',
  styleUrls: ['./pipeline-graph.component.sass']
})
export class PipelineGraphComponent implements OnInit {
  @Output() deleteClicked: EventEmitter<string> = new EventEmitter();
  @Output() jobStartClicked: EventEmitter<string> = new EventEmitter();

  @Input() pipeline: Pipeline;
  @Input() jobs: Job[];

  @ViewChild('jobMenu', { static: false }) jobMenu;

  public pgraph: PipelineGraph;
  public currentJob: Job;

  constructor(
    private element: ElementRef,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.pgraph = new PipelineGraph();
  }

  ngOnInit() {
  }

  redraw() {
    this.pgraph.calculate(this.jobs);
  }

  getGraphHeight() {
    return this.pgraph.collection.reduce((max, row) =>
      Math.max(max, row.reduce((max, box) => Math.max(max, box.y_offset), 0))
    , 0) + 100;
  }

  getJobIconForStatus(status) {
    switch (status) {
      case 'idle':
        return { icon: 'query_builder', color: '#212121' };
      case 'waiting':
        return { icon: 'pause_circle_outline', color: '#FFB74D' };
      case 'running':
        return { icon: 'play_circle_outline', color: '#42A5F5' };
      case 'stopping':
        return { icon: 'stop_circle_outline', color: '#EF5350' };
      case 'failed':
        return { icon: 'highlight_off', color: '#E57373' };
      case 'succeeded':
        return { icon: 'check_circle_outline', color: '#4CAF50'};
      default:
        return { icon: '', color: '#000' };
    }
  }

  generateLineStyle(line) {
    if (!line || !line.points) {
      return "";
    }

    let [x1, y1, x2, y2] = line.points;

    let a = x1 - x2;
    let b = y1 - y2;
    let c = Math.sqrt(a*a + b*b);

    let cx = (x1 + x2) / 2;
    let cy = (y1 + y2) / 2;

    let x = cx - c / 2;
    let y = cy;

    var alpha = Math.PI - Math.atan2(-b, a);

    return `top: ${y}px; left: ${x}px; width: ${c}px; transform: rotate(${alpha}rad);`;
  }

  showJobMenu(e, job) {
    e.stopPropagation();
    e.preventDefault();
    this.currentJob = job;
  }

  onJobEdit() {
    this.router.navigate(['jobs', this.currentJob.id, 'edit']);
  }

  onJobRemove() {
    this.deleteClicked.emit(String(this.currentJob.id));
  }

  onJobStart() {
    this.jobStartClicked.emit(String(this.currentJob.id));
  }
}
