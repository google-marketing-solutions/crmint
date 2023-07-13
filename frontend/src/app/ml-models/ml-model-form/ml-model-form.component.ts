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
  Variable, BigQueryDataset, Timespan, Source, Destination, Output, Role
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
  destinations: string[];
  cachedVariables: Variable[] = [];
  fetchingVariables: boolean = false;
  submitting: boolean = false;

  constructor(
    private _fb: UntypedFormBuilder,
    private mlModelsService: MlModelsService,
    private router: Router,
    private route: ActivatedRoute) {
      this.title = this.router.url.endsWith('new') ? 'New Machine-Learning Model' : 'Edit Machine-Learning Model';
      this.createForm();
      this.types = Object.values(Type).filter(type => type !== Type.LOGISTIC_REG);
      this.uniqueIds = Object.values(UniqueId);
      this.destinations = Object.values(Destination);
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
      variables: this._fb.array([]),
      conversionRateSegments: [0, [Validators.required, Validators.pattern(/^[0-9]*$/)]],
      classImbalance: [4, [Validators.required, Validators.min(1), Validators.max(10)]],
      timespans: this._fb.array([]),
      output: this._fb.group({
        destination: [null, [Validators.required, this.enumValidator(Destination)]],
        parameters: this._fb.group({
          customerId: [null, Validators.pattern(/^[0-9]*$/)],
          conversionActionId: [null, Validators.pattern(/^[0-9]*$/)],
          averageConversionValue: [null, Validators.pattern(/^[0-9]*\.{0,1}[0-9]*$/)]
        })
      })
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
        this.refreshTimespans();
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
      conversionRateSegments: this.mlModel.conversion_rate_segments,
      classImbalance: this.mlModel.class_imbalance,
      output: {
        destination: this.mlModel.output.destination,
        parameters: {
          customerId: this.mlModel.output.parameters.customer_id,
          conversionActionId: this.mlModel.output.parameters.conversion_action_id,
          averageConversionValue: this.mlModel.output.parameters.average_conversion_value
        }
      }
    });

    this.refreshTimespans();
    this.refreshHyperParameters();
    this.refreshVariables();
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

  get type() {
    const type = this.value('type');
    return {
      isClassification: Object.keys(ClassificationType).includes(type),
      isRegression: Object.keys(RegressionType).includes(type)
    }
  }

  get variables() {
    return this.mlModelForm.get('variables') as UntypedFormArray;
  }

  get hyperParameters() {
    return this.mlModelForm.get('hyperParameters') as UntypedFormArray;
  }

  get timespans() {
    return this.mlModelForm.get('timespans') as UntypedFormArray;
  }

  get output() {
    let output = this.mlModelForm.get('output').value;
    let requirements = [];
    switch (output.destination) {
      case Destination.GOOGLE_ADS_OFFLINE_CONVERSION:
        requirements = ['customerId', 'conversionActionId'];
        break;
    }
    if (this.type.isClassification) {
      requirements.push('averageConversionValue');
    }
    output.requirements = requirements;

    return output;
  }

  /**
   * Provides a quick unified way to check all the necessary parameters exist
   * that are required to properly fetch the ml model variables.
   */
  get variableRequirementsProvided() {
    const bigQueryDatasetName = this.value('bigQueryDataset', 'name');
    const bigQueryDatasetLocation = this.value('bigQueryDataset', 'location');
    const usesFirstPartyData = this.value('usesFirstPartyData');
    const timespans = this.value('timespans');

    if (!bigQueryDatasetName || !bigQueryDatasetLocation) {
      return false;
    }

    if (usesFirstPartyData === null) {
      return false;
    }

    for (const timespan of timespans) {
      if (timespan.value <= 0) {
        return false;
      }
    }

    return true;
  }

  /**
   * Get variables (feature, label, and other options) from GA4 Events and First Party tables in BigQuery.
   */
  async getVariables() {
    if (this.cachedVariables.length === 0) {
      try {
        this.fetchingVariables = true;
        const dataset = this.value('bigQueryDataset');
        const ts = this.value('timespans');
        const variables = await this.mlModelsService.getVariables(dataset, ts);
        variables.sort((a: Variable, b: Variable) => {
          return a.source.localeCompare(b.source);
        });
        this.cachedVariables = variables;
        this.errorMessage = '';
      } catch (error) {
        this.errorMessage = error || 'An error occurred';
      } finally {
        this.fetchingVariables = false;
      }
    }

    const usesFirstPartyData = this.value('usesFirstPartyData');
    if (!usesFirstPartyData) {
      return this.cachedVariables.filter(v => v.source !== Source.FIRST_PARTY);
    }
    return this.cachedVariables;
  }

  /**
   * Take the provided variables and toggle the requisite checkboxes
   * and set the variable roles within the form.
   *
   * @param variables
   */
  async refreshVariables() {
    const formVariables = this.value('variables');
    const roles = Object.values(Role);
    const firstPartyRoles = roles;
    const googleAnalyticsRoles = roles.filter(r => ![Role.TRIGGER_DATE, Role.CLIENT_ID, Role.USER_ID].includes(r));
    const existingVariables = formVariables.length ? formVariables : this.mlModel.variables;
    const variables = await this.getVariables();
    let controls = [];

    for (const variable of variables) {
      const existingVariable = existingVariables?.find(v => v.name === variable.name && v.source === variable.source);

      variable.roles = variable.source === Source.FIRST_PARTY ? firstPartyRoles : googleAnalyticsRoles;
      if (this.type.isClassification) {
        variable.roles = variable.roles.filter(r => ![Role.FIRST_VALUE].includes(r));
      }

      variable.role = existingVariable ? existingVariable.role : null;
      variable.keyRequired = false;
      variable.hint = null;

      if (existingVariable && existingVariable.key) {
        variable.key = existingVariable.key;
        variable.value_type = variable.parameters.find(p => p.key === variable.key).value_type;
      } else if (variable.parameters.length === 1) {
        variable.key = variable.parameters[0].key;
        variable.value_type = variable.parameters[0].value_type;
      }

      if (variable.role === Role.LABEL) {
        if (variable.source == Source.GOOGLE_ANALYTICS) {
          variable.keyRequired = true;
          variable.hint = 'Due to your selection, trigger date will be derrived from the date associated with the first value ' +
                          'and the first value (if not selected) defaults to the first label value.';
        }
      }

      if (variable.role === Role.FIRST_VALUE && variable.source === Source.GOOGLE_ANALYTICS) {
        variable.keyRequired = true;
      }

      controls.push(this._fb.group({
        name: [variable.name],
        source: [variable.source, this.enumValidator(Source)],
        count: [variable.count],
        roles: [variable.roles],
        role: [variable.role, this.enumValidator(Role)],
        parameters: [variable.keyRequired ? variable.parameters : null],
        key: [
          variable.key,
          variable.keyRequired ? [Validators.required] : []
        ],
        value_type: [variable.value_type],
        hint: variable.hint
      }));
    }

    this.mlModelForm.setControl('variables', this._fb.array(controls));
  }

  /**
   * Reset variables to empty array. Necessary when modifying parameters that affect
   * which variables are available for selection and requires a manual refresh.
   */
  resetVariables() {
    this.cachedVariables = [];
    this.mlModelForm.setControl('variables', this._fb.array([]));
  }

  /**
   * Take the provided hyper parameters and set/update associated controls within the form.
   */
  refreshHyperParameters() {
    const formHyperParameters = this.value('hyperParameters');
    const existingParams = formHyperParameters.length ? formHyperParameters : this.mlModel.hyper_parameters;
    const modelType = this.value('type');
    const params = MlModel.getDefaultHyperParameters(modelType);
    let controls = [];

    for (let param of params) {
      const existingParam = existingParams?.find(p => p.name === param.name);
      param.toggled = existingParam ? true : false;
      param.value = existingParam ? existingParam.value : param.value;

      controls.push(this._fb.group({
        name: [param.name],
        value: param.range ? [param.value, [Validators.min(param.range.min), Validators.max(param.range.max)]] : [param.value],
        toggled: [existingParam ? param.toggled : true],
        range: [param.range],
        options: [param.options]
      }));
    }

    this.mlModelForm.setControl('hyperParameters', this._fb.array(controls));
  }

  /**
   * Take the provided timespans and set/update associated controls within the form.
   *
   * @param existingTimespans The list of existing timespans returned from the backend.
   */
  refreshTimespans() {
    const existingTimespans = this.mlModel.timespans;
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
   * Handles ensuring the output config fields are updated appropriately when form fields that
   * affect what's allowed to be selected are changed.
   */
  refreshOutput() {
    const output = this.output;
    const allRequirementsFields = Object.keys(output.parameters);

    if (output.requirements.length > 0) {
      for (const requirement of output.requirements) {
        this.mlModelForm.get(['output', 'parameters', requirement]).addValidators(Validators.required);
      }
    } else {
      for (const requirement of allRequirementsFields) {
        this.mlModelForm.get(['output', 'parameters', requirement]).removeValidators(Validators.required);
      }
    }

    for (const requirement of allRequirementsFields) {
      this.mlModelForm.get(['output', 'parameters', requirement]).setValue(null);
    }
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
    this.mlModel.variables = formModel.variables.filter(v => v.role !== null) as Variable[];
    this.mlModel.conversion_rate_segments = formModel.conversionRateSegments as number;
    this.mlModel.class_imbalance = formModel.classImbalance as number;
    this.mlModel.timespans = formModel.timespans as Timespan[];
    this.mlModel.output = {
      destination: formModel.output.destination as string,
      parameters: {
        customer_id: formModel.output.parameters.customerId as string,
        conversion_action_id: formModel.output.parameters.conversionActionId as string,
        average_conversion_value: parseFloat(formModel.output.parameters.averageConversionValue)
      }
    } as Output;
  }

  /**
   * Update the ml model object using the form data and send it to the backend to persist.
   */
  async save() {
    this.submitting = true;
    this.prepareSaveMlModel();

    if (this.mlModel.id) {
      try {
        this.mlModel.validate();
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
   * A validator helper that checks the value against a provided enum to make sure it's a valid option.
   *
   * @param e The enum to validate against.
   * @returns A validator function that is used by the form to determine accuracy.
   */
  private enumValidator(e: object): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      return !Object.values(e).includes(control.value) && control.value !== null ? {invalidSelection: {value: control.value}} : null;
    };
  }
}
