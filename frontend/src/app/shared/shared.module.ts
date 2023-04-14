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

import {CommonModule} from '@angular/common';
import {CUSTOM_ELEMENTS_SCHEMA, NgModule} from '@angular/core';
import {MatDatepickerModule} from '@angular/material/datepicker';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/legacy-button';
import {MatCardModule} from '@angular/material/legacy-card';
import {MatCheckboxModule} from '@angular/material/legacy-checkbox';
import {MatNativeDateModule} from '@angular/material/legacy-core';
import {MatFormFieldModule} from '@angular/material/legacy-form-field';
import {MatInputModule} from '@angular/material/legacy-input';
import {MatMenuModule} from '@angular/material/legacy-menu';
import {MatProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatSelectModule} from '@angular/material/legacy-select';
import {MatSlideToggleModule} from '@angular/material/legacy-slide-toggle';
import {MatTabsModule} from '@angular/material/legacy-tabs';
import {MatToolbarModule} from '@angular/material/toolbar';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {StatusComponent} from './status/status.component';

@NgModule({
  imports: [
    CommonModule,
    MatButtonModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatCardModule,
    MatSlideToggleModule,
    MatSelectModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatTabsModule,
    MatCheckboxModule,
    MatMenuModule
  ],
  declarations: [
    StatusComponent,
  ],
  exports: [
    StatusComponent,
    MatButtonModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatCardModule,
    MatSlideToggleModule,
    MatSelectModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatTabsModule,
    MatCheckboxModule,
    MatMenuModule
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class SharedModule { }
