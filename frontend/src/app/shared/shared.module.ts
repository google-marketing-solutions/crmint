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

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSelectModule } from '@angular/material/select';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { StatusComponent } from './status/status.component';

@NgModule({
  imports: [
    CommonModule,
    MatButtonModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatCardModule,
    MatSlideToggleModule,
    MatSelectModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatTabsModule,
    MatCheckboxModule
  ],
  declarations: [
    StatusComponent
  ],
  exports: [
    StatusComponent,
    MatButtonModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatCardModule,
    MatSlideToggleModule,
    MatSelectModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatTabsModule,
    MatCheckboxModule
  ]
})
export class SharedModule { }
