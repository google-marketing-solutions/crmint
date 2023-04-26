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
  Validators, ValidatorFn, ValidationErrors, AbstractControl
} from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { plainToClass } from 'class-transformer';

import { MlModelsService } from '../shared/ml-models.service';
import {
  MlModel, Type, ClassificationType, RegressionType, UniqueId, HyperParameter,
  Feature, Label, Variable, BigQueryDataset, Timespan, Source
} from 'app/models/ml-model';

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
  submitting: boolean = false;

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
        averageValue: [0.0, Validators.required]
      }),
      classImbalance: [4, [Validators.required, Validators.min(1), Validators.max(10)]],
      timespans: this._fb.array([])
    });
  }

  /**
   * If an id param exists pull and load the configuration associated with it.
   * Otherwise load any necessary data required to configure a new model.
   */
  ngOnInit() {
    this.route.params.subscribe(params => {
      const id = params['id'];
      if (id) {
        this.loadConfiguration(id)
          .then(() => this.state = 'loaded')
          .catch(error => {
            if (error === 'model-not-found') {
              this.router.navigate(['ml-models']);
            } else {
              this.errorMessage = error.toString();
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
   * Pull configuration and load the values into the form.
   *
   * @param id The id of the ml model.
   */
  async loadConfiguration(id: number) {
    try {
      const mlModel = await this.mlModelsService.get(id);
      this.mlModel = plainToClass(MlModel, mlModel as MlModel);
      await this.fetchVariables(this.mlModel.bigquery_dataset);
      this.assignMlModelToForm();
    } catch (error) {
      if (error && error.status === 404) {
        throw 'model-not-found';
      } else {
        throw error;
      }
    }
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
        averageValue: this.mlModel.label.average_value
      },
      classImbalance: this.mlModel.class_imbalance
    });

    this.setHyperParameters(this.mlModel.hyper_parameters, this.mlModel.type);
    this.setFeatures(this.mlModel.features);
    this.setTimespans(this.mlModel.timespans);
    this.updateLabelKeyValidator();
  }

  get type() {
    const type = this.value('type');
    return {
      isClassification: Object.values(ClassificationType).includes(type),
      isRegression: Object.values(RegressionType).includes(type)
    }
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
   *
   * @param bigQueryDataset The dataset to use when fetching first party variables
   *                        (only required for loading an existing model).
   */
  async fetchVariables(bigQueryDataset: Object = null) {
    this.fetchingVariables = true;
    try {
      const dataset = bigQueryDataset || this.value('bigQueryDataset');
      let variables = await this.mlModelsService.getVariables(dataset);
      this.variables = plainToClass(Variable, variables as Variable[]);
      this.errorMessage = '';
    } catch (error) {
      this.errorMessage = error || 'An error occurred';
    } finally {
      this.fetchingVariables = false;
    }
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
    } else {
      const features = this.features.value as Feature[];
      for (const index of features.keys()) {
        const f = features[index];
        if (f.name === feature.name) {
          this.features.removeAt(index);
          break;
        }
      }
    }
    this.refreshLabel();
  }

  /**
   * Resets label name and key in the event an update to the available labels cases the currently
   * selected label to no longer be available. Also resets output settings based on whether the
   * label is considered a score or revenue.
   */
  refreshLabel() {
    const labels = this.labels;
    const label = this.label;

    const labelField = {
      name: this.mlModelForm.get(['label', 'name']),
      key: this.mlModelForm.get(['label', 'key']),
      source: this.mlModelForm.get(['label', 'source']),
      valueType: this.mlModelForm.get(['label', 'valueType'])
    }

    if (!labels.find(label => label.name === labelField.name.value)) {
      labelField.name.setValue('');
      labelField.key.setValue('');
    }

    if (label.name) {
      // set source automatically in the form based on label selected.
      labelField.source.setValue(label.source);

      // if the selected key is not available anymore due to label change then unset it.
      if (!label.parameters.find(param => param.key === label.key)) {
        labelField.key.setValue('');
      }

      // if there's only one option auto-select and disable the field otherwise make sure the field is enabled.
      if (label.parameters.length === 1) {
        labelField.key.setValue(label.parameters[0].key);
      }

      // set value type automatically in the form based on label and key selected.
      if (label.key) {
        labelField.valueType.setValue(label.valueType);
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
   * Add/Remove select-box option descriptions.
   *
   * @param toggled Whether or not to show the option descriptions.
   */
  toggleOptionDescriptions(toggled: boolean) {
    this.optionDescriptions = toggled;
  }

  /**
   * Enforces option description visibility while also formatting the description appropriately.
   *
   * @param description The description to show.
   * @returns The formatted description if option descriptions are enabled.
   */
  optionDescription(description: string): string {
    return this.optionDescriptions ? description : '';
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
      average_value: parseFloat(formModel.label.averageValue)
    } as Label;
    this.mlModel.class_imbalance = formModel.classImbalance as number;
    this.mlModel.timespans = formModel.timespans as Timespan[];
  }

  /**
   * Update the ml model object using the form data and send it to the backend to persist.
   */
  async save() {
    this.submitting = true;
    this.prepareSaveMlModel();

    if (this.mlModel.id) {
      try {
        await this.mlModelsService.update(this.mlModel);
        this.router.navigate(['ml-models', this.mlModel.id]);
        this.errorMessage = '';
      } catch (error) {
        this.errorMessage = error || 'An error occurred';
      }
    } else {
      const mlModel = await this.mlModelsService.create(this.mlModel)
      this.router.navigate(['ml-models', mlModel.id]);
    }

    this.submitting = false;
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
