// Copyright 2023 Google Inc
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
export class MlModelsService extends ApiService {

  private url = `${this.getHost()}/ml-models`;

  getAll() {
    this.removeContentTypeHeader();
    return this.http.get(this.url, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  get(id) {
    this.removeContentTypeHeader();
    return this.http.get(this.url + '/' + id)
                    .toPromise()
                    .catch(this.handleError);
  }

  create(model) {
    this.addContentTypeHeader();
    return this.http.post(this.url, JSON.stringify(model), this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  update(model) {
    this.addContentTypeHeader();
    return this.http.put(this.url + '/' + model.id, JSON.stringify(model), this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  delete(id) {
    this.removeContentTypeHeader();
    return this.http.delete(this.url + '/' + id)
                    .toPromise()
                    .catch(this.handleError);
  }

  getVariables(bigquery_dataset) {
    this.removeContentTypeHeader();
    this.options.params = {
      dataset_name: bigquery_dataset.name,
      dataset_location: bigquery_dataset.location
    };
    return this.http.get(this.url + '/variables', this.options)
                    .toPromise()
                    .catch(this.handleError);
  }
}
