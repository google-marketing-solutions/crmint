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

import { Component, OnInit } from '@angular/core';
import {
  UntypedFormGroup, UntypedFormBuilder, UntypedFormArray,
  Validators, ValidatorFn, ValidationErrors, AbstractControl, UntypedFormControl
} from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { plainToClass } from 'class-transformer';

import { MlModelsService } from '../shared/ml-models.service';
import { MlModel, Type, UniqueId, HyperParameter, Feature, Label, Variable, BigQueryDataset, Timespan, Source } from 'app/models/ml-model';

@Component({
  selector: 'app-ml-model-form',
  templateUrl: './ml-model-form.component.html',
  styleUrls: ['./ml-model-form.component.sass']
})
export class MlModelFormComponent implements OnInit {

  mlModelForm: UntypedFormGroup;
  mlModel: MlModel = new MlModel();
  state: string = 'loading'; // state has one of values: loading, loaded or error
  title: string = '';
  errorMessage: string = '';
  uniqueIds: string[];
  types: string[];
  variables: Variable[] = [];
  optionDescriptions: boolean = false;
  fetchingVariables: boolean = false;

  // TODO: Why is it not valid when the entire form is filled out?

  constructor(
    private _fb: UntypedFormBuilder,
    private mlModelsService: MlModelsService,
    private router: Router,
    private route: ActivatedRoute) {
      this.title = this.router.url.endsWith('new') ? 'New Machine-Learning Model' : 'Edit Machine-Learning Model';
      this.createForm();
      this.types = Object.values(Type).filter(type => type !== 'LOGISTIC_REG');
      this.uniqueIds = Object.values(UniqueId);
    }

  /**
   * Create the base form, including general structure, defaults, and validators.
   */
  createForm() {
    this.mlModelForm = this._fb.group({
      name: ['', [Validators.required, Validators.pattern(/^[a-z][a-z0-9 _-]*$/i)]],
      bigQueryDataset: this._fb.group({
        name: ['', [Validators.required, Validators.pattern(/^[a-z][a-z0-9_-]*$/i)]],
        location: ['US', [Validators.required, Validators.pattern(/^[a-z]{2,}$/i)]]
      }),
      type: [null, [Validators.required, this.enumValidator(Type)]],
      uniqueId: [null, [Validators.required, this.enumValidator(UniqueId)]],
      usesFirstPartyData: [null, Validators.required],
      hyperParameters: this._fb.array([]),
      features: this._fb.array([]),
      label: this._fb.group({
        name: ['', [Validators.required, Validators.pattern(/^[a-z][a-z0-9_-]*$/i)]],
        source: ['', [Validators.required, Validators.pattern(/^[A-Z_]*$/i)]],
        key: ['', [Validators.required, Validators.pattern(/^[a-z][a-z0-9_-]*$/i)]],
        valueType: ['', Validators.pattern(/^[a-z]*$/i)],
        isRevenue: [null, Validators.required],
        isScore: [null, Validators.required],
        isPercentage: [false, Validators.required],
        isConversion: [false, Validators.required],
        averageValue: [0.0, Validators.required]
      }),
      skewFactor: [4, [Validators.required, Validators.min(0), Validators.max(10)]],
      timespans: this._fb.array([])
    });
  }

  /**
   * Get the user's GA4 event list and if an id was provided as a URL parameter
   * get the associated ml model data for that id.
   */
  ngOnInit() {
    this.route.params.subscribe(params => {
      const id = params['id'];
      if (id) {
        this.mlModelsService.get(id)
          .then(mlModel => {
            this.mlModel = plainToClass(MlModel, mlModel as MlModel);
            return this.fetchVariables();
          })
          .then(() => {
            this.assignMlModelToForm();
            this.state = 'loaded';
          })
          .catch(response => {
            if (response.status === 404) {
              this.router.navigate(['ml-models']);
            } else {
              this.state = 'error';
            }
          });
      } else {
        this.setTimespans();
        this.state = 'loaded';
      }
    });
  }

  /**
   * Takes the ml model data currently set and updates the form to match.
   */
  assignMlModelToForm() {
    this.mlModelForm.reset({
      name: this.mlModel.name,
      bigQueryDataset: {
        name: this.mlModel.bigquery_dataset.name,
        location: this.mlModel.bigquery_dataset.location
      },
      type: this.mlModel.type,
      uniqueId: this.mlModel.unique_id,
      usesFirstPartyData: this.mlModel.uses_first_party_data,
      label: {
        name: this.mlModel.label.name,
        source: this.mlModel.label.source,
        key: this.mlModel.label.key,
        valueType: this.mlModel.label.value_type,
        isRevenue: this.mlModel.label.is_revenue,
        isScore: this.mlModel.label.is_score,
        isPercentage: this.mlModel.label.is_percentage,
        isConversion: this.mlModel.label.is_conversion,
        averageValue: this.mlModel.label.average_value
      },
      skewFactor: this.mlModel.skew_factor
    });

    this.setHyperParameters(this.mlModel.hyper_parameters, this.mlModel.type);
    this.setFeatures(this.mlModel.features);
    this.setTimespans(this.mlModel.timespans);
    this.updateLabelKeyValidator();
  }

  get analyticsVariables() {
    return this.variables.filter(variable => variable.source === Source.GOOGLE_ANALYTICS)
  }

  get firstPartyVariables() {
    return this.variables.filter(variable => variable.source === Source.FIRST_PARTY)
  }

  get features() {
    return this.mlModelForm.get('features') as UntypedFormArray;
  }

  get hyperParameters() {
    return this.mlModelForm.get('hyperParameters') as UntypedFormArray;
  }

  get timespans() {
    return this.mlModelForm.get('timespans') as UntypedFormArray;
  }

  get labels() {
    const usesFirstPartyData = this.value('usesFirstPartyData');
    if (usesFirstPartyData) {
      return this.variables.filter(variable => !this.featureSelected(variable));
    } else {
      return this.variables.filter(variable => !this.featureSelected(variable) && variable.source !== Source.FIRST_PARTY);
    }
  }

  get label() {
    let label = this.mlModelForm.get('label').value;
    if (label.name) {
      const variable = this.variables.find(variable => variable.name === label.name);

      label.parameters = variable.parameters;
      label.source = variable.source;
      label.isFirstParty = variable.source === Source.FIRST_PARTY;

      if (label.key) {
        const keyParameter = variable.parameters.find(param => param.key === label.key);
        if (keyParameter) {
          label.valueType = keyParameter.value_type;
        }
      }
    }
    return label;
  }

  /**
   * Fetch variables (feature and label options) from GA4 Events and First Party tables in BigQuery.
   */
  fetchVariables() {
    this.fetchingVariables = true;
    return this.mlModelsService.getVariables(this.mlModel)
      .then(variables => this.variables = plainToClass(Variable, variables as Variable[]))
      .catch(response => {
        this.errorMessage = response || 'An error occurred';
      })
      .finally(() => this.fetchingVariables = false);
  }

  /**
   * Helper for quickly getting a control's value.
   *
   * @param control The name of the control or the control itself.
   * @param key The key within the control to lookup the value for.
   * @returns The value of the control.
   */
  value(control: string|AbstractControl, key: string = ''): any {
    let formControl = control instanceof AbstractControl ? control : this.mlModelForm.get(control);
    return key ? formControl.get(key).value : formControl.value;
  }

  /**
   * Helper to quickly identify whether or not a feature has been selected/checked.
   *
   * @param {Variable} variable The variable to check if selected as a feature.
   * @returns {boolean} Whether or not the feature provided was selected/checked.
   */
  featureSelected(variable: Variable): boolean {
    const features: Feature[] = this.features.value;
    const exists = features.find(f => f.name === variable.name && f.source === variable.source);
    return exists ? true : false;
  }

  /**
   * Change the hyper-parameter selection based on model type provided.
   *
   * @param type The model type.
   */
  updateHyperParameters(type: Type) {
    this.setHyperParameters(this.mlModel.hyper_parameters, type);
  }

  /**
   * Looks up feature by name provided and toggles it (changes to true if false and false if true).
   *
   * @param feature The feature to lookup & toggle.
   * @param toggled **true** or **false**.
   */
  toggleFeature(feature: Feature, toggled: boolean) {
    if (toggled) {
      this.features.push(this._fb.control(feature as Feature));
      this.refreshLabel();
    } else {
      const index = this.features.value.indexOf(feature);
      if (index !== -1) {
        this.features.removeAt(index);
      }
    }
  }

  /**
   * Resets label name and key in the event an update to the available labels cases the currently
   * selected label to no longer be available. Also resets output settings based on whether the
   * label is considered a score or revenue.
   */
  refreshLabel() {
    const labels = this.labels;
    const label = this.label;

    const nameField = this.mlModelForm.get(['label', 'name']);
    const keyField = this.mlModelForm.get(['label', 'key']);
    const sourceField = this.mlModelForm.get(['label', 'source']);
    const valueTypeField = this.mlModelForm.get(['label', 'valueType']);
    const isRevenueField = this.mlModelForm.get(['label', 'isRevenue']);
    const isPercentageField = this.mlModelForm.get(['label', 'isPercentage']);
    const isConversionField = this.mlModelForm.get(['label', 'isConversion']);
    const averageValueField = this.mlModelForm.get(['label', 'averageValue']);

    if (!labels.find(label => label.name === nameField.value)) {
      nameField.setValue('');
      keyField.setValue('');
    }

    if (label.name) {
      // set source automatically in the form based on label selected.
      sourceField.setValue(label.source);

      // if the selected key is not available anymore due to label change then unset it.
      if (!label.parameters.find(param => param.key === label.key)) {
        keyField.setValue('');
      }

      // if there's only one option auto-select and disable the field otherwise make sure the field is enabled.
      if (label.parameters.length === 1) {
        keyField.setValue(label.parameters[0].key);
      }

      // most option fields are related to the ouput being a score so update accordingly.
      if (label.isScore) {
        isRevenueField.setValue(false);
      } else {
        isRevenueField.setValue(true);
        isPercentageField.setValue(false);
        isConversionField.setValue(false);
        averageValueField.setValue(0.0);
      }

      // set value type automatically in the form based on label and key selected.
      if (label.key) {
        valueTypeField.setValue(label.valueType);
      }
    }
  }

  /**
   * Updates the label key validator based on whether or not the data source includes first party data.
   * With first party data: label key is not required.
   * Without first party data: label key is required.
   */
  updateLabelKeyValidator() {
    const usesFirstPartyData = this.value('usesFirstPartyData');
    const labelKeyField = this.mlModelForm.get('label').get('key');
    if (usesFirstPartyData) {
      labelKeyField.removeValidators(Validators.required);
    } else {
      labelKeyField.addValidators(Validators.required);
    }
    labelKeyField.updateValueAndValidity();
  }

  /**
   * Uppercase the first character in the word(s) provided (word split into multiple words on underscore).
   *
   * @param word The word(s) you want to capitalize.
   * @returns The capitalized word.
   */
  capitalize(word: string): string {
    let formattedParts = [];
    for (const part of word.split('_')) {
      formattedParts.push(part.charAt(0).toUpperCase() + part.slice(1).toLowerCase());
    }

    return formattedParts.join(' ');
  }

  /**
   * Remove select-box option descriptions.
   */
  removeOptionDescriptions() {
    this.optionDescriptions = false;
  }

  /**
   * Add select-box option descriptions.
   */
  addOptionDescriptions() {
    this.optionDescriptions = true;
  }

  /**
   * Translate the form data and update the ml model with these prepared values.
   */
  prepareSaveMlModel() {
    let formModel = this.mlModelForm.value;

    this.mlModel.name = formModel.name as string;
    this.mlModel.bigquery_dataset = formModel.bigQueryDataset as BigQueryDataset;
    this.mlModel.type = formModel.type as Type;
    this.mlModel.unique_id = formModel.uniqueId as UniqueId;
    this.mlModel.uses_first_party_data = formModel.usesFirstPartyData as boolean;
    this.mlModel.hyper_parameters = formModel.hyperParameters as HyperParameter[];
    this.mlModel.features = formModel.features.map(feature => {
      return {
        name: feature.name,
        source: feature.source
      }
    });
    this.mlModel.label = {
      name: formModel.label.name as string,
      source: formModel.label.source as Source,
      key: formModel.label.key as string,
      value_type: formModel.label.valueType as string,
      is_revenue: formModel.label.isRevenue as boolean,
      is_score: formModel.label.isScore as boolean,
      is_percentage: formModel.label.isPercentage as boolean,
      is_conversion: formModel.label.isConversion as boolean,
      average_value: parseFloat(formModel.label.averageValue)
    } as Label;
    this.mlModel.skew_factor = formModel.skewFactor as number;
    this.mlModel.timespans = formModel.timespans as Timespan[];
  }

  /**
   * Update the ml model object using the form data and send it to the backend to persist.
   */
  save() {
    this.prepareSaveMlModel();

    if (this.mlModel.id) {
      this.mlModelsService.update(this.mlModel)
        .then(() => {
          this.router.navigate(['ml-models', this.mlModel.id]);
          this.errorMessage = '';
        }).catch(response => {
          this.errorMessage = response || 'An error occurred';
        });
    } else {
      this.mlModelsService.create(this.mlModel)
        .then((mlModel) => this.router.navigate(['ml-models', mlModel.id]));
    }
  }

  /**
   * Route the user back to the appropriate page upon cancel.
   */
  cancel() {
    if (this.mlModel.id) {
      this.router.navigate(['ml-models', this.mlModel.id]);
    } else {
      this.router.navigate(['ml-models']);
    }
  }

  /**
   * Take the provided hyper parameters and set/update associated controls within the form.
   *
   * @param existingParams The list of parameters returned from the backend.
   * @param type The type of model.
   */
  private setHyperParameters(existingParams: HyperParameter[], type: Type) {
    const params = MlModel.getDefaultHyperParameters(type);
    let controls = [];

    for (let param of params) {
      const existingParam = existingParams?.find(existingParam => existingParam.name === param.name);
      param.toggled = existingParam ? true : false;
      if (existingParam) {
        param.value = existingParam.value;
      }
      controls.push(this._fb.group({
        name: [param.name],
        value: param.range ? [param.value, [Validators.min(param.range.min), Validators.max(param.range.max)]] : [param.value],
        toggled: [param.toggled || true],
        range: [param.range],
        options: [param.options]
      }));
    }

    this.mlModelForm.setControl('hyperParameters', this._fb.array(controls));
  }

  /**
   * Take the provided features and toggle the requisite checkboxes within the form.
   *
   * @param features
   */
  private setFeatures(features: Feature[]) {
    for (const feature of features) {
      this.toggleFeature(feature, true);
    }
  }

  /**
   * Take the provided timespans and set/update associated controls within the form.
   *
   * @param existingTimespans The list of existing timespans returned from the backend.
   */
  private setTimespans(existingTimespans: Timespan[] = []) {
    const timespans = MlModel.getDefaultTimespans();
    let controls = [];

    for (const timespan of timespans) {
      const existingTimespan = existingTimespans?.find(existingTimespan => existingTimespan.name === timespan.name);
      if (existingTimespan) {
        timespan.value = existingTimespan.value;
        timespan.unit = existingTimespan.unit;
      }
      controls.push(this._fb.group({
        name: [timespan.name],
        value: [timespan.value, [Validators.required, Validators.min(timespan.range.min), Validators.max(timespan.range.max)]],
        range: [timespan.range],
        unit: [timespan.unit]
      }));
    }

    this.mlModelForm.setControl('timespans', this._fb.array(controls));
  }

  /**
   * A validator helper that checks the value against a provided enum to make sure it's a valid option.
   *
   * @param e The enum to validate against.
   * @returns A validator function that is used by the form to determine accuracy.
   */
  private enumValidator(e: object): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      return !Object.values(e).includes(control.value) ? {invalidSelection: {value: control.value}} : null;
    };
  }
}
