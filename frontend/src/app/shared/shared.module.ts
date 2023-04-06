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
import {MatLegacyButtonModule} from '@angular/material/button';
import {MatLegacyCardModule} from '@angular/material/card';
import {MatLegacyCheckboxModule} from '@angular/material/checkbox';
import {MatLegacyNativeDateModule} from '@angular/material/core';
import {MatDatepickerModule} from '@angular/material/datepicker';
import {MatLegacyFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyInputModule} from '@angular/material/input';
import {MatLegacyMenuModule} from '@angular/material/menu';
import {MatLegacyProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatLegacySelectModule} from '@angular/material/select';
import {MatLegacySlideToggleModule} from '@angular/material/slide-toggle';
import {MatLegacyTabsModule} from '@angular/material/tabs';
import {MatToolbarModule} from '@angular/material/toolbar';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {StatusComponent} from './status/status.component';

@NgModule({
  imports: [
    CommonModule, MatLegacyButtonModule, MatDatepickerModule,
    MatLegacyNativeDateModule, MatLegacyFormFieldModule, MatLegacyInputModule,
    MatLegacyProgressSpinnerModule, MatIconModule, MatLegacyCardModule,
    MatLegacySlideToggleModule, MatLegacySelectModule, BrowserAnimationsModule,
    MatToolbarModule, MatLegacyTabsModule, MatLegacyCheckboxModule,
    MatLegacyMenuModule
  ],
  declarations: [
    StatusComponent,
  ],
  exports: [
    StatusComponent, MatLegacyButtonModule, MatDatepickerModule,
    MatLegacyNativeDateModule, MatLegacyFormFieldModule, MatLegacyInputModule,
    MatLegacyProgressSpinnerModule, MatIconModule, MatLegacyCardModule,
    MatLegacySlideToggleModule, MatLegacySelectModule, BrowserAnimationsModule,
    MatToolbarModule, MatLegacyTabsModule, MatLegacyCheckboxModule,
    MatLegacyMenuModule
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class SharedModule {
}
