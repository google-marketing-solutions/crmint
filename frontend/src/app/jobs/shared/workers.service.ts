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

@Injectable()
export class WorkersService extends ApiService {

  private url = `${this.getHost()}/workers`;

  protected getHost() {
    return super.getHost().replace(':8080/', ':8081/');
  }

  getParamsForWorkerClass(worker_class) {
    this.removeContentTypeHeader();
    return this.http.get(this.getWorkerParamsUrl(worker_class))
                    .toPromise()
                    .catch(this.handleError);
  }

  getWorkers() {
    this.removeContentTypeHeader();
    return this.http.get(this.url)
                    .toPromise()
                    .catch(this.handleError);
  }

  private getWorkerParamsUrl(worker_class) {
    return `${this.getHost()}/workers/${worker_class}/params`;
  }
}
