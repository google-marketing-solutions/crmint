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
import { Pipeline } from 'app/models/pipeline';

@Injectable()
export class PipelinesService extends ApiService {

  private url = `${this.getHost()}/pipelines`;

  getPipelines() {
    return this.http.get(this.url, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  getPipeline(id) {
    return this.http.get(this.getPipelineUrl(id))
                    .toPromise()
                    .catch(this.handleError);
  }

  addPipeline(pipeline) {
    return this.http.post(this.url, JSON.stringify(pipeline), this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  updatePipeline(pipeline) {
    return this.http.put(this.getPipelineUrl(pipeline.id), JSON.stringify(pipeline), this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  deletePipeline(id) {
    return this.http.delete(this.getPipelineUrl(id))
                    .toPromise()
                    .catch(this.handleError);
  }

  startPipeline(id) {
    return this.http.post(this.getPipelineUrl(id) + '/start', {}, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  stopPipeline(id) {
    return this.http.post(this.getPipelineUrl(id) + '/stop', {}, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  importPipeline(file: File) {
    const formData: FormData = new FormData();
    formData.append('upload_file', file, file.name);
    return this.http.post(this.url + '/import', formData)
                    .toPromise()
                    .catch(this.handleError);
  }

  exportPipeline(id) {
    return this.http.get(this.getPipelineUrl(id) + '/export', {observe: 'response'})
                    .toPromise()
                    .catch(this.handleError);
  }

  updateRunOnSchedule(id, run_on_schedule) {
    return this.http.patch(this.getPipelineUrl(id) + '/run_on_schedule', {run_on_schedule: run_on_schedule}, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  private getPipelineUrl(id) {
    return this.url + '/' + id;
  }

  getLogs(id, params) {
    const url = this.getPipelineUrl(id) + '/logs';
    // for (const k of Object.keys(params)) {
    //   if (!this.options.params.has(k)) {
    //     this.options.params.set(k, params[k]);
    //   }
    // }
    this.options.params = Object.assign({}, params, this.options.params);

    return this.http.get(url, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

}
