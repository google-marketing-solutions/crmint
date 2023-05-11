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

import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'labelcase'
})
export class LabelcasePipe implements PipeTransform {
  specialCaseMap: Object = {api: 'API', id: 'ID', bigquery: 'BigQuery'};

  /**
   * Uppercase the first character in the word(s) provided (word split into
   * multiple words on underscore). Handles special cases like id, api, etc
   * according to an internal mapping.
   *
   * @param value The word(s) you want to capitalize.
   * @returns The capitalized word(s).
   */
  transform(value: any, args?: any): any {
    let formattedParts = [];
    for (const part of value.split('_')) {
      if (Object.keys(this.specialCaseMap).includes(part.toLowerCase())) {
        formattedParts.push(this.specialCaseMap[part.toLowerCase()]);
      } else {
        formattedParts.push(
            part.charAt(0).toUpperCase() + part.slice(1).toLowerCase());
      }
    }

    return formattedParts.join(' ');
  }
}
