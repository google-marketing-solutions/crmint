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

import { StagesComponent } from './dashboard/stages/stages.component';
import { SharedModule } from './shared/shared.module';
import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ClipboardModule } from 'ngx-clipboard';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { SettingsComponent } from './settings/settings.component';
import { PipelinesModule } from './pipelines/pipelines.module';
import { PipelinesRoutingModule } from './pipelines/pipelines-routing.module';
import { JobsModule } from './jobs/jobs.module';
import { JobsRoutingModule } from './jobs/jobs-routing.module';
import { NavBarComponent } from './nav-bar/nav-bar.component';
import { TopBarComponent } from './top-bar/top-bar.component';
import { LabelcasePipe } from './pipes/labelcase.pipe';
import { StagesService } from './dashboard/shared/stages.service';
import { DashboardPipelinesComponent } from 'app/dashboard/dashboard-pipelines/dashboard-pipelines.component';

@NgModule({
  declarations: [
    AppComponent,
    DashboardComponent,
    DashboardPipelinesComponent,
    SettingsComponent,
    NavBarComponent,
    TopBarComponent,
    StagesComponent,
    LabelcasePipe,
],
  imports: [
    BrowserModule,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    PipelinesModule,
    PipelinesRoutingModule,
    JobsModule,
    JobsRoutingModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    ClipboardModule,
    SharedModule
  ],
  providers: [
    StagesService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
