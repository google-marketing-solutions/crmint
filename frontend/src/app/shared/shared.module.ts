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
import { MatLegacyButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatLegacyNativeDateModule } from '@angular/material/core';
import { MatLegacyFormFieldModule } from '@angular/material/form-field';
import { MatLegacyInputModule } from '@angular/material/input';
import { MatLegacyProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatLegacyCardModule } from '@angular/material/card';
import { MatLegacySlideToggleModule } from '@angular/material/slide-toggle';
import { MatLegacySelectModule } from '@angular/material/select';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatLegacyTabsModule } from '@angular/material/tabs';
import { MatLegacyCheckboxModule } from '@angular/material/checkbox';
import { MatLegacyMenuModule } from '@angular/material/menu';
import { NgModule, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';

import { StatusComponent } from './status/status.component';

@NgModule({
  imports: [
    CommonModule,
    MatLegacyButtonModule,
    MatDatepickerModule,
    MatLegacyNativeDateModule,
    MatLegacyFormFieldModule,
    MatLegacyInputModule,
    MatLegacyProgressSpinnerModule,
    MatIconModule,
    MatLegacyCardModule,
    MatLegacySlideToggleModule,
    MatLegacySelectModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatLegacyTabsModule,
    MatLegacyCheckboxModule,
    MatLegacyMenuModule
  ],
  declarations: [
    StatusComponent,
  ],
  exports: [
    StatusComponent,
    MatLegacyButtonModule,
    MatDatepickerModule,
    MatLegacyNativeDateModule,
    MatLegacyFormFieldModule,
    MatLegacyInputModule,
    MatLegacyProgressSpinnerModule,
    MatIconModule,
    MatLegacyCardModule,
    MatLegacySlideToggleModule,
    MatLegacySelectModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatLegacyTabsModule,
    MatLegacyCheckboxModule,
    MatLegacyMenuModule
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class SharedModule { }
