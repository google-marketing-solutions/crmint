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
import { Http, Headers, RequestOptions, URLSearchParams } from '@angular/http';
import 'rxjs/add/operator/toPromise';

import { ApiService } from 'app/api.service';
import { Pipeline } from 'app/models/pipeline';

@Injectable()
export class PipelinesService extends ApiService {

  private url = `${this.getHost()}/pipelines`;

  getPipelines() {
    return this.http.get(this.url, this.options)
                    .toPromise()
                    .then(res => res.json() as Pipeline[])
                    .catch(this.handleError);
  }

  getPipeline(id) {
    return this.http.get(this.getPipelineUrl(id))
                    .toPromise()
                    .then(res => res.json() as Pipeline)
                    .catch(this.handleError);
  }

  addPipeline(pipeline) {
    return this.http.post(this.url, JSON.stringify(pipeline), this.options)
                    .toPromise()
                    .then(res => res.json() as Pipeline)
                    .catch(this.handleError);
  }

  updatePipeline(pipeline) {
    return this.http.put(this.getPipelineUrl(pipeline.id), JSON.stringify(pipeline), this.options)
                    .toPromise()
                    .then(res => res.json() as Pipeline)
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
                    .then(res => res.json() as Pipeline)
                    .catch(this.handleError);
  }

  stopPipeline(id) {
    return this.http.post(this.getPipelineUrl(id) + '/stop', {}, this.options)
                    .toPromise()
                    .then(res => res.json() as Pipeline)
                    .catch(this.handleError);
  }

  importPipeline(file: File) {
    const formData: FormData = new FormData();
    formData.append('upload_file', file, file.name);
    const headers = new Headers();
    const options = new RequestOptions({ headers: headers });
    return this.http.post(this.url + '/import', formData, options)
                    .toPromise()
                    .then(res => res.json())
                    .catch(this.handleError);
  }

  exportPipeline(id) {
    return this.http.get(this.getPipelineUrl(id) + '/export')
                    .toPromise()
                    .catch(this.handleError);
  }

  updateRunOnSchedule(id, run_on_schedule) {
    return this.http.patch(this.getPipelineUrl(id) + '/run_on_schedule', {run_on_schedule: run_on_schedule}, this.options)
                    .toPromise()
                    .then(res => res.json() as Pipeline)
                    .catch(this.handleError);
  }

  private getPipelineUrl(id) {
    return this.url + '/' + id;
  }

  getLogs(id, params) {
    const url = this.getPipelineUrl(id) + '/logs';
    const p = new URLSearchParams();
    for (const k of Object.keys(params)) {
      if (params[k] !== null) {
        p.set(k, params[k]);
      }
    }

    this.options.search = p;
    return this.http.get(url, this.options)
                    .toPromise()
                    .then(res => res.json())
                    .catch(this.handleError);
  }

}
