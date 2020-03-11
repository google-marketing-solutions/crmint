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

import { Injectable } from '@angular/core';

import { ApiService } from 'app/api.service';
import { Config, Setting } from 'app/config';
import { Param } from 'app/models/param';

@Injectable()
export class SettingsService extends ApiService {

  private configUrl = `${this.host}/configuration`;
  private variablesUrl = `${this.host}/global_variables`;
  private settingsUrl = `${this.host}/general_settings`;

  getConfigData(): Promise<Config> {
    this.removeContentTypeHeader();
    return this.http.get(this.configUrl)
               .toPromise()
               .catch(this.handleError);
  }

  saveVariables(variables: Param[]): Promise<Param[]> {
    this.addContentTypeHeader();
    return this.http.put(this.variablesUrl, {variables: variables})
               .toPromise()
               .catch(this.handleError);
  }

  saveSettings(settings: Setting[]) {
    this.addContentTypeHeader();
    return this.http.put(this.settingsUrl, {settings: settings})
               .toPromise()
               .catch(this.handleError);
  }
}
