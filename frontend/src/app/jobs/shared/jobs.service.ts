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
import { serialize } from 'class-transformer';
import 'rxjs/add/operator/toPromise';

import { Param } from 'app/models/param';
import { ApiService } from 'app/api.service';

@Injectable()
export class JobsService extends ApiService {

  private url = `${this.getHost()}/jobs`;

  getJobsByPipeline(pipeline_id) {
    const params = new URLSearchParams();
    params.set('pipeline_id', pipeline_id);
    this.options.search = params;
    return this.http.get(this.url, this.options)
                    .toPromise()
                    .then(res => res.json())
                    .catch(this.handleError);
  }

  getJob(id) {
    return this.http.get(this.getJobUrl(id))
                    .toPromise()
                    .then(res => res.json())
                    .catch(this.handleError);
  }

  addJob(job) {
    this.addContentTypeHeader();
    return this.http.post(this.url, serialize(job), { headers: this.headers })
                    .toPromise()
                    .then(res => res.json())
                    .catch(this.handleError);
  }

  updateJob(job) {
    this.addContentTypeHeader();
    return this.http.put(this.getJobUrl(job.id), serialize(job), { headers: this.headers })
                    .toPromise()
                    .then(res => res.json())
                    .catch(this.handleError);
  }

  deleteJob(id) {
    this.addContentTypeHeader();
    return this.http.delete(this.getJobUrl(id))
                    .toPromise()
                    .then(res => res.json())
                    .catch(this.handleError);
  }

  startJob(id) {
    this.addContentTypeHeader();
    return this.http.post(this.getJobUrl(id) + '/start', null, { headers: this.headers })
                    .toPromise()
                    .then(res => res.json())
                    .catch(this.handleError);
  }

  private getJobUrl(id) {
    return this.url + '/' + id;
  }

}
