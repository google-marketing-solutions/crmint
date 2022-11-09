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
import { HttpClient } from '@angular/common/http';

const IP_ADDRESS_REGEX = /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/i;

@Injectable()
export class ApiService {

  protected host = this.getHost();
  protected options: any = {
    headers: {}
  };

  constructor(protected http: HttpClient) { }

  protected getHost() {
    const h = window.location.hostname;
    if (h === 'localhost') {
      return `http://${h}:8080/api`
    }
    else if (IP_ADDRESS_REGEX.test(h)) {
      return `http://${h}/api`
    } else {
      // Force HTTPS
      return `https://${h}/api`
    }
  }

  protected handleError(error: any): Promise<any> {
    console.error('An error occurred', error); // for demo purposes only
    return Promise.reject((error.error && error.error.message) || error.message || error);
  }

  protected addContentTypeHeader() {
    this.options.headers['Content-Type'] = 'application/json';
  }

  protected removeContentTypeHeader() {
    delete this.options.headers['Content-Type'];
  }
}
