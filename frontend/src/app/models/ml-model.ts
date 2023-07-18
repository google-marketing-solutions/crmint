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

export enum RegressionType {
  BOOSTED_TREE_REGRESSOR = 'BOOSTED_TREE_REGRESSOR',
  DNN_REGRESSOR = 'DNN_REGRESSOR',
  RANDOM_FOREST_REGRESSOR = 'RANDOM_FOREST_REGRESSOR',
  LINEAR_REG = 'LINEAR_REG'
}

export enum ClassificationType {
  BOOSTED_TREE_CLASSIFIER = 'BOOSTED_TREE_CLASSIFIER',
  DNN_CLASSIFIER = 'DNN_CLASSIFIER',
  RANDOM_FOREST_CLASSIFIER = 'RANDOM_FOREST_CLASSIFIER',
  LOGISTIC_REG = 'LOGISTIC_REG'
}

export enum UniqueId {
  CLIENT_ID = 'CLIENT_ID',
  USER_ID = 'USER_ID'
}

export enum Source {
  GOOGLE_ANALYTICS = 'GOOGLE_ANALYTICS',
  FIRST_PARTY = 'FIRST_PARTY',
  GOOGLE_ANALYTICS_AND_FIRST_PARTY = 'GOOGLE_ANALYTICS_AND_FIRST_PARTY'
}

export enum Destination {
  GOOGLE_ANALYTICS_MP_EVENT = 'GOOGLE_ANALYTICS_MP_EVENT',
  GOOGLE_ADS_OFFLINE_CONVERSION = 'GOOGLE_ADS_OFFLINE_CONVERSION'
}

export type Range = {
  min: number;
  max: number;
  step: number;
}

export class HyperParameter {
  name: string;
  _value: string|number|boolean;
  toggled?: boolean = true;
  range?: Range;
  options?: string[];

  constructor(config: object) {
    for (const key in config) {
      const value = config[key];
      this[key] = value;
    }
  }

  set value(v: string|number|boolean) {
    let value = v;
    if (typeof value === 'string') {
      if (value.match(/^\d+$/)) {
        value = parseInt(value);
      } else if (value.match(/^\d*\.\d+$/)) {
        value = parseFloat(value);
      } else if (value.match(/^(true|false)$/i)) {
        value = value.toLowerCase() === 'true';
      }
    }
    this._value = value;
  }

  get value(): string|number|boolean {
    return this._value;
  }

  get disabled(): boolean {
    return !this.options && !this.range;
  }
}

export enum Role {
  FEATURE = 'FEATURE',
  LABEL = 'LABEL',
  TRIGGER_DATE = 'TRIGGER_DATE',
  FIRST_VALUE = 'FIRST_VALUE',
  USER_ID = 'USER_ID',
  CLIENT_ID = 'CLIENT_ID'
}

type Parameter = {
  key: string;
  value_type: string;
}

export type Variable = {
  name: string;
  source: string;
  count: number;
  roles?: Role[];
  role?: Role;
  parameters?: Parameter[];
  key?: string;
  value_type?: string;
  hint?: string;
  key_required?: boolean;
}

export type BigQueryDataset = {
  name: string;
  location: string;
}

export type Timespan = {
  name: string;
  value: number;
  unit: string;
  range?: Range;
}

type InputParameters = {
  first_party_dataset: string;
  first_party_table: string;
}

export type Input = {
  source: Source;
  parameters: InputParameters;
  requirements?: string[];
}

type OutputParameters = {
  customer_id: string;
  conversion_action_id: string;
  average_conversion_value: number;
}

export type Output = {
  destination: Destination;
  parameters: OutputParameters;
  requirements?: string[];
}

export class MlModel {
  id: number;
  name: string;
  input: Input;
  bigquery_dataset: BigQueryDataset;
  type: Type;
  unique_id: UniqueId;
  hyper_parameters: HyperParameter[];
  variables: Variable[];
  conversion_rate_segments: number;
  class_imbalance: number;
  timespans: Timespan[];
  output: Output;
  pipelines: Pipeline[];
  updated_at: string;

  /**
   * Return a set of default hyper-parameters based on the model type provided.
   *
   * @param type The model type.
   * @returns A hyper-parameter list.
   */
  static getDefaultHyperParameters(type: Type): HyperParameter[] {
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

  /**
   * Get default timespans and associated configurations.
   *
   * @returns A timespan list.
   */
  static getDefaultTimespans(): Timespan[] {
    let configs = [
      {
        name: 'training',
        value: 30,
        unit: 'day',
        range: {min: 1, max: 1825, step: 1}
      },
      {
        name: 'predictive',
        value: 1,
        unit: 'day',
        range: {min: 1, max: 365, step: 1}
      }
    ];

    let timespans = []
    for (const config of configs) {
      timespans.push(config as Timespan);
    }
    return timespans;
  }

  /**
   * Checks the data in the model to ensure it's valid.
   *
   * @throws {Error} Error message with the details of why it failed validation.
   */
  validate() {
    // ensure that one variable has the LABEL role.
    if (this.variables.filter(v => v.role === Role.LABEL).length !== 1) {
      throw new Error('The role of "Label" must be applied to one variable.');
    }

    // ensure there is no more than one variable assigned the role TRIGGER_DATE.
    if (this.variables.filter(v => v.role === Role.TRIGGER_DATE).length > 1) {
      throw new Error('The role of "Trigger Date" must only be applied to one variable.');
    }

    // ensure there is no more than one variable assigned the role FIRST_VALUE.
    if (this.variables.filter(v => v.role === Role.FIRST_VALUE).length > 1) {
      throw new Error('The role of "First Value" must only be applied to one variable.');
    }

    // if using first party data, validate client or user id is selected based on unique id selection.
    if (this.input.source.includes(Source.FIRST_PARTY)) {
      switch (this.unique_id) {
        case UniqueId.CLIENT_ID:
          if (this.variables.filter(v => v.role === Role.CLIENT_ID).length !== 1) {
            throw new Error('The role of "Client ID" must be applied to one variable.');
          }
        case UniqueId.USER_ID:
          if (this.variables.filter(v => v.role === Role.USER_ID).length !== 1) {
            throw new Error('The role of "User ID" must be applied to one variable.');
          }
      }
    }

    // if regression model and a first party label is selected then a first party first value and trigger date and if you use GA4 label then you can select a GA4 first_value, but not a first_party one.
    // for regression models a first value and trigger date are required.
    // if using a label sourced from Google Analytics trigger date is derrived from the date associated with the first value and the first value (if not selected) defaults to the first label value.
    if (Object.keys(RegressionType).includes(this.type)) {
      const label: Variable = this.variables.filter(v => v.role === Role.LABEL)[0];
      switch (label.source) {
        case Source.FIRST_PARTY:
          if (this.variables.filter(v => v.role === Role.FIRST_VALUE).length !== 1) {
            throw new Error('The role of "First Value" must be applied to one variable.');
          }

          if (this.variables.filter(v => v.role === Role.TRIGGER_DATE).length !== 1) {
            throw new Error('The role of "Trigger Date" must be applied to one variable.');
          }
          break;
        case Source.GOOGLE_ANALYTICS:
          const firstValue: Variable = this.variables.filter(v => v.role === Role.FIRST_VALUE)[0];
          if (firstValue.source === Source.FIRST_PARTY) {
            throw new Error('The role of "First Value" must be applied to one variable sourced from Google Analytics since the selected label is sourced from there.');
          }
          break;
      }
    }
  }

  toJSON() {
    return {
      id: this.id,
      name: this.name,
      input: this.input,
      bigquery_dataset: this.bigquery_dataset,
      type: this.type,
      unique_id: this.unique_id,
      hyper_parameters: this.hyper_parameters.map(param => {
        if (param.toggled) {
          return {
            name: param.name,
            value: `${param.value}`
          };
        }
      }),
      variables: this.variables.map(variable => {
        return {
          name: variable.name,
          source: variable.source,
          role: variable.role,
          key: variable.key,
          value_type: variable.value_type
        }
      }),
      conversion_rate_segments: this.conversion_rate_segments,
      class_imbalance: this.class_imbalance,
      timespans: this.timespans.map(timespan => {
        return {
          name: timespan.name,
          value: timespan.value,
          unit: timespan.unit
        };
      }),
      output: this.output
    }
  }
}
