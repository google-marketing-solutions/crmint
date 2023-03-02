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

import { Pipeline } from './pipeline';

export enum Type {
  LOGISTIC_REG = 'LOGISTIC_REG',
  BOOSTED_TREE_REGRESSOR = 'BOOSTED_TREE_REGRESSOR',
  BOOSTED_TREE_CLASSIFIER = 'BOOSTED_TREE_CLASSIFIER'
}

export enum UniqueId {
  CLIENT_ID = 'CLIENT_ID',
  USER_ID = 'USER_ID'
}

export enum Source {
  GOOGLE_ANALYTICS = 'GOOGLE_ANALYTICS',
  FIRST_PARTY = 'FIRST_PARTY'
}

export class Range {
  min: number
  max: number
  step: number
}

export class HyperParameter {
  name: string
  _value: string
  toggled?: boolean = true
  range?: Range
  options?: string[]

  constructor(config: object) {
    for (const key in config) {
      const value = config[key];
      this[key] = value;
    }
  }

  set value(v: any) {
    let value = v;
    if (typeof value === 'string') {
      if (value.match(/^\d+$/)) {
        value = parseInt(value);
      } else if (v.match(/^\d*\.\d+$/)) {
        value = parseFloat(value);
      } else if (value.match(/^(true|false)$/i)) {
        value = value.toLowerCase() === 'true';
      }
    }
    this._value = value;
  }

  get value(): any {
    return this._value;
  }

  get disabled(): boolean {
    return !this.options && !this.range;
  }
}

export class Feature {
  name: string
  source: string
}

export class Label {
  name: string
  source: string
  key: string
  value_type: string
}

class Parameter {
  key: string;
  value_type: string;
}

export class Variable {
  name: string;
  source: string;
  count: number;
  parameters: Parameter[];
}

export class BigQueryDataset {
  name: string;
  location: string;
}

export class Timespan {
  name: string;
  value: number;
  unit: string;
  range?: Range

  constructor(config: object) {
    for (const key in config) {
      const value = config[key];
      this[key] = value;
    }
  }
}

export class MlModel {
  id: number;
  name: string;
  bigquery_dataset: BigQueryDataset;
  type: Type;
  unique_id: UniqueId;
  uses_first_party_data: boolean;
  hyper_parameters: HyperParameter[];
  features: Feature[];
  label: Label;
  skew_factor: number;
  timespans: Timespan[];
  pipelines: Pipeline[];
  updated_at: string;

  public static getDefaultHyperParameters(type: Type): HyperParameter[] {
    let configs = [];
    switch (type) {
      case Type.LOGISTIC_REG:
        configs = [
          {
            name: 'L1_REG',
            value: 1
          },
          {
            name: 'L2_REG',
            value: 1
          },
          {
            name: 'DATA_SPLIT_METHOD',
            value: 'AUTO_SPLIT',
            options: ['AUTO_SPLIT','RANDOM','CUSTOM','SEQ','NO_SPLIT']
          }
        ];
        break;
      case Type.BOOSTED_TREE_REGRESSOR:
        configs = [
          {
            name: 'L1_REG',
            value: 1
          },
          {
            name: 'L2_REG',
            value: 1
          },
          {
            name: 'BOOSTER_TYPE',
            value: 'GBTREE',
            options: ['GBTREE', 'DART']
          },
          {
            name: 'MAX_ITERATIONS',
            value: 50,
            range: {min: 25, max: 100, step: 5}
          },
          {
            name: 'SUBSAMPLE',
            value: 0.80,
            range: {min: 0.25, max: 1.0, step: 0.1}
          },
          {
            name: 'TREE_METHOD',
            value: 'HIST',
            options: ['AUTO','EXACT','APPROX','HIST']
          },
          {
            name: 'ENABLE_GLOBAL_EXPLAIN',
            value: true,
            options: [true, false]
          },
          {
            name: 'NUM_PARALLEL_TREE',
            value: 2,
            range: {min: 1, max: 10, step: 1}
          },
          {
            name: 'DATA_SPLIT_METHOD',
            value: 'AUTO_SPLIT',
            options: ['AUTO_SPLIT','RANDOM','CUSTOM','SEQ','NO_SPLIT']
          },
          {
            name: 'EARLY_STOP',
            value: false,
            options: [true, false]
          }
        ];
        break;
        case Type.BOOSTED_TREE_CLASSIFIER:
        configs = [
          {
            name: 'AUTO_CLASS_WEIGHTS',
            value: true,
            options: [true, false]
          },
          {
            name: 'MAX_ITERATIONS',
            value: 50,
            range: {min: 25, max: 100, step: 5}
          },
          {
            name: 'SUBSAMPLE',
            value: 0.80,
            range: {min: 0.25, max: 1.0, step: 0.1}
          },
          {
            name: 'ENABLE_GLOBAL_EXPLAIN',
            value: true,
            options: [true, false]
          },
          {
            name: 'NUM_PARALLEL_TREE',
            value: 2,
            range: {min: 1, max: 10, step: 1}
          },
          {
            name: 'DATA_SPLIT_METHOD',
            value: 'AUTO_SPLIT',
            options: ['AUTO_SPLIT','RANDOM','CUSTOM','SEQ','NO_SPLIT']
          },
          {
            name: 'EARLY_STOP',
            value: false,
            options: [true, false]
          }
        ];
        break;
    }

    let params = []
    for (const config of configs) {
      params.push(new HyperParameter(config));
    }
    return params;
  }

  public static getDefaultTimespans(): Timespan[] {
    let configs = [
      {
        name: 'training',
        value: 6,
        unit: 'month',
        range: {min: 1, max: 24, step: 1}
      },
      {
        name: 'predictive',
        value: 1,
        unit: 'month',
        range: {min: 1, max: 12, step: 1}
      }
    ];

    let timespans = []
    for (const config of configs) {
      timespans.push(new Timespan(config));
    }
    return timespans;
  }

  public toJSON() {
    return {
      id: this.id,
      name: this.name,
      bigquery_dataset: this.bigquery_dataset,
      type: this.type,
      unique_id: this.unique_id,
      uses_first_party_data: this.uses_first_party_data,
      hyper_parameters: this.hyper_parameters.map(param => {
        if (param.toggled) {
          return {
            name: param.name,
            value: `${param.value}`
          };
        }
      }),
      features: this.features.map(feature => {
        return {
          name: feature.name,
          source: feature.source
        };
      }),
      label: {
        name: this.label.name,
        key: this.label.key,
        value_type: this.label.value_type,
        source: this.label.source
      },
      skew_factor: this.skew_factor,
      timespans: this.timespans.map(timespan => {
        return {
          name: timespan.name,
          value: timespan.value,
          unit: timespan.unit
        };
      }),
    }
  }
}
