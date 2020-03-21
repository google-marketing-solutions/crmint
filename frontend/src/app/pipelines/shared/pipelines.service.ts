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
export class PipelinesService extends ApiService {

  private url = `${this.getHost()}/pipelines`;

  getPipelines() {
    this.removeContentTypeHeader();
    return this.http.get(this.url, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  getPipeline(id) {
    this.removeContentTypeHeader();
    return this.http.get(this.getPipelineUrl(id))
                    .toPromise()
                    .catch(this.handleError);
  }

  addPipeline(pipeline) {
    this.addContentTypeHeader();
    return this.http.post(this.url, JSON.stringify(pipeline), this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  updatePipeline(pipeline) {
    this.addContentTypeHeader();
    return this.http.put(this.getPipelineUrl(pipeline.id), JSON.stringify(pipeline), this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  deletePipeline(id) {
    this.removeContentTypeHeader();
    return this.http.delete(this.getPipelineUrl(id))
                    .toPromise()
                    .catch(this.handleError);
  }

  startPipeline(id) {
    this.addContentTypeHeader();
    return this.http.post(this.getPipelineUrl(id) + '/start', {}, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  stopPipeline(id) {
    this.addContentTypeHeader();
    return this.http.post(this.getPipelineUrl(id) + '/stop', {}, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  importPipeline(file: File) {
    const formData: FormData = new FormData();
    formData.append('upload_file', file, file.name);
    this.removeContentTypeHeader();
    return this.http.post(this.url + '/import', formData)
                    .toPromise()
                    .catch(this.handleError);
  }

  exportPipeline(id) {
    this.removeContentTypeHeader();
    return this.http.get(this.getPipelineUrl(id) + '/export', {observe: 'response'})
                    .toPromise()
                    .catch(this.handleError);
  }

  updateRunOnSchedule(id, run_on_schedule) {
    this.addContentTypeHeader();
    return this.http.patch(this.getPipelineUrl(id) + '/run_on_schedule', {run_on_schedule: run_on_schedule}, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

  private getPipelineUrl(id) {
    return this.url + '/' + id;
  }

  getLogs(id, params) {
    const url = this.getPipelineUrl(id) + '/logs'
    const p = {};
    for (const k of Object.keys(params)) {
      if (params[k] !== null) {
        p[k] = params[k];
      }
    }

    this.options.params = p;
    this.removeContentTypeHeader();
    return this.http.get(url, this.options)
                    .toPromise()
                    .catch(this.handleError);
  }

}
