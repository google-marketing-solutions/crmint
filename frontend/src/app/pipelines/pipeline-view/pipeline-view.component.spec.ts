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

/* tslint:disable:no-unused-variable */
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterModule } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { JobsService } from '../../jobs/shared/jobs.service';
import { PipelinesService } from '../../pipelines/shared/pipelines.service';
import { PipelineViewComponent } from './pipeline-view.component';

describe('PipelineViewComponent', () => {
  let component: PipelineViewComponent;
  let fixture: ComponentFixture<PipelineViewComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientModule,
        RouterModule.forRoot([])
      ],
      providers: [
        JobsService,
        PipelinesService
      ],
      declarations: [ PipelineViewComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(PipelineViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
