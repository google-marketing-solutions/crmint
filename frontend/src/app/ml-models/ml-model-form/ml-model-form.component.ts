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
import { State } from 'app/models/shared';
import {
  MlModel, Type, ClassificationType, RegressionType, UniqueId, HyperParameter,
  Variable, BigQueryDataset, Timespan, Source, Destination, Input, Output, Role, Comparison
} from 'app/models/ml-model';

const MIN_NUM_OF_FEATURES = 2;

@Component({
  selector: 'app-ml-model-form',
  templateUrl: './ml-model-form.component.html',
  styleUrls: ['./ml-model-form.component.sass']
})
export class MlModelFormComponent implements OnInit {

  mlModelForm: UntypedFormGroup;
  mlModel: MlModel = new MlModel();
  state: string = State.LOADING;
  title: string = '';
  errorMessage: string = '';
  uniqueIds: string[];
  types: string[];
  sources: string[];
  destinations: string[];
  cachedVariables: Variable[] = [];
  fetchingVariables: boolean = false;
  variableSelectOpen: number = -1;

  constructor(
    private _fb: UntypedFormBuilder,
    private mlModelsService: MlModelsService,
    private router: Router,
    private route: ActivatedRoute) {
      this.title = this.router.url.endsWith('new') ? 'New Machine-Learning Model' : 'Edit Machine-Learning Model';
      this.createForm();
      this.types = Object.keys(Type).filter(type => type !== Type.LOGISTIC_REG);
      this.uniqueIds = Object.keys(UniqueId);
      this.sources = Object.keys(Source);
      this.destinations = Object.keys(Destination);
    }

  /**
   * Create the base form, including general structure, defaults, and validators.
   */
  createForm() {
    this.mlModelForm = this._fb.group({
      name: ['', [Validators.required, Validators.pattern(/^[a-z][a-z0-9 _-]*$/i)]],
      input: this._fb.group({
        source: ['', [Validators.required, this.enumValidator(Source)]],
        parameters: this._fb.group({
          googleAnalyticsProject: [null, Validators.pattern(/^[a-z][a-z0-9 _-]*$/i)],
          googleAnalyticsDataset: [null, Validators.pattern(/^[a-z][a-z0-9 _-]*$/i)],
          firstPartyProject: [null, Validators.pattern(/^[a-z][a-z0-9 _-]*$/i)],
          firstPartyDataset: [null, Validators.pattern(/^[a-z][a-z0-9 _-]*$/i)],
          firstPartyTable: [null, Validators.pattern(/^[a-z][a-z0-9 _-]*$/i)]
        })
      }),
      bigQueryDataset: this._fb.group({
        name: ['', [Validators.required, Validators.pattern(/^[a-z][a-z0-9_-]*$/i)]],
        location: ['US', [Validators.required, Validators.pattern(/^[a-z]{2,}$/i)]]
      }),
      type: [null, [Validators.required, this.enumValidator(Type)]],
      uniqueId: [null, [Validators.required, this.enumValidator(UniqueId)]],
      hyperParameters: this._fb.array([]),
      variables: this._fb.array([]),
      conversionRateSegments: [0, [Validators.required, Validators.pattern(/^[0-9]*$/)]],
      classImbalance: [4, [Validators.required, Validators.min(1), Validators.max(100)]],
      timespans: this._fb.array([]),
      output: this._fb.group({
        destination: ['', [Validators.required, this.enumValidator(Destination)]],
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
  async ngOnInit() {
    this.route.params.subscribe(async params => {
      const id = params['id'];
      try {
        if (id) {
          await this.loadConfiguration(id);
          this.refreshInput();
          this.refreshTimespans();
          this.refreshHyperParameters();
          this.refreshOutput();
          await this.fetchVariables();
        } else {
          this.refreshTimespans();
        }
        this.state = State.LOADED;
      } catch (error) {
        if (error === 'model-not-found') {
          this.router.navigate(['ml-models']);
        } else {
          this.errorMessage = error.toString();
          this.state = State.ERROR;
        }
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
      this.mlModel.variables.sort((a: Variable, b: Variable) => {
        const aCompare = `${a.role + a.source + a.name}`;
        const bCompare = `${b.role + b.source + b.name}`;
        return aCompare.localeCompare(bCompare);
      });
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
      input: {
        source: this.mlModel.input.source,
        parameters: {
          googleAnalyticsProject: this.mlModel.input.parameters.google_analytics_project,
          googleAnalyticsDataset: this.mlModel.input.parameters.google_analytics_dataset,
          firstPartyProject: this.mlModel.input.parameters.first_party_project,
          firstPartyDataset: this.mlModel.input.parameters.first_party_dataset,
          firstPartyTable: this.mlModel.input.parameters.first_party_table
        }
      },
      bigQueryDataset: {
        name: this.mlModel.bigquery_dataset.name,
        location: this.mlModel.bigquery_dataset.location
      },
      type: this.mlModel.type,
      uniqueId: this.mlModel.unique_id,
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
  }

  /**
   * Helper for quickly getting a control's value.
   *
   * @param control The name of the control or the control itself.
   * @param key The key within the control to lookup the value for (optional).
   * @returns The value of the control.
   */
  value(control: string|AbstractControl, key: string = ''): any {
    const formControl = control instanceof AbstractControl ? control : this.mlModelForm.get(control);
    const targetControl = key ? formControl.get(key) : formControl;
    return targetControl ? targetControl.value : null;
  }

  /**
   * Return any error for a given control.
   *
   * @param control The control itself.
   * @returns The error associated with the control (if any) or undefined otherwise.
   */
  error(control: AbstractControl): string|undefined {
    return control.errors ? Object.keys(control.errors)[0] : undefined;
  }

  get type() {
    const type: Type = this.mlModelForm.get('type').value;
    return {
      isClassification: Object.keys(ClassificationType).includes(type),
      isRegression: Object.keys(RegressionType).includes(type)
    }
  }

  get input() {
    let input: Input = this.mlModelForm.get('input').value;

    input.requirements = [];
    if (input.source.includes(Source.GOOGLE_ANALYTICS)) {
      input.requirements.push('googleAnalyticsProject', 'googleAnalyticsDataset');
    }

    if (input.source.includes(Source.FIRST_PARTY)) {
      input.requirements.push('firstPartyProject', 'firstPartyDataset', 'firstPartyTable');
    }

    return input;
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
    let output: Output = this.mlModelForm.get('output').value;
    const isClassificationModel = this.type.isClassification;

    output.requirements = [];
    switch (output.destination) {
      case Destination.GOOGLE_ADS_OFFLINE_CONVERSION:
        output.requirements = ['customerId', 'conversionActionId'];
        break;
    }
    if (isClassificationModel) {
      output.requirements.push('averageConversionValue');
    }

    return output;
  }

  /**
   * Provides a quick unified way to check all the necessary parameters exist
   * that are required to properly fetch the ml model variables.
   */
  get variableRequirementsProvided(): boolean {
    const bigQueryDataset = this.value('bigQueryDataset');
    const input = this.value('input');
    const timespans: Timespan[] = this.value('timespans');

    if (!bigQueryDataset.name || !bigQueryDataset.location) {
      return false;
    }

    if (input.source === null) {
      return false;
    } else {
      if (input.source.includes(Source.FIRST_PARTY)) {
        if (!input.parameters.firstPartyProject || !input.parameters.firstPartyDataset || !input.parameters.firstPartyTable) {
          return false;
        }
      }
      if (input.source.includes(Source.GOOGLE_ANALYTICS)) {
        if (!input.parameters.googleAnalyticsProject || !input.parameters.googleAnalyticsDataset) {
          return false;
        }
      }
    }

    for (const timespan of timespans) {
      if (timespan.value <= 0) {
        return false;
      }
    }

    return true;
  }

  /**
   * Check the model variables selected to ensure the necessary variables have been
   * specified and if not return any errors that would require user correction.
   *
   * @returns List of validation errors if any and otherwise returns undefined.
   */
  get variableErrors(): string[]|undefined {
    let errors = [];

    const source: Source = this.value('input', 'source');
    const variables: Variable[] = this.value('variables');

    this.checkMinimumNumberOfFeatures(variables, errors);
    this.checkOneLabel(variables, errors);

    if (source.includes(Source.FIRST_PARTY)) {
      this.checkUniqueId(variables, errors);
      this.checkGCLID(variables, errors);
      this.checkTriggerDate(variables, errors);
    }

    return errors.length > 0 ? errors : undefined;
  }

  /**
   * Dynamically updates required input parameters based on the input source selected.
   */
  refreshInput() {
    const input: Input = this.input;
    const allRequirementsFields: string[] = Object.keys(input.parameters);

    for (const requirement of allRequirementsFields) {
      const field = this.mlModelForm.get(['input', 'parameters', requirement]);
      if (input.requirements.includes(requirement)) {
        field.addValidators(Validators.required);
      } else {
        field.removeValidators(Validators.required);
        field.setValue(null);
      }
    }
  }

  /**
   * Adds a new variable form control to the form array "variables". This creates a new entry where
   * the user can start to fill in the necessary fields for defining a variable and how the backend
   * should use/add that variable to the model via the templates.
   */
  addVariable() {
    const variables: Variable[] = this.getVariables();
    const variableSources: string[] = variables.map(v => v.source).filter((s, i, a) => a.indexOf(s) === i);

    const formVariables = this.mlModelForm.get('variables') as UntypedFormArray;
    formVariables.push(this._fb.group({
      sources: [variableSources],
      source: [variableSources.length === 1 ? variableSources[0] : null]
    }));
    if (variableSources.length === 1) {
      this.refreshVariables();
    }
  }

  /**
   * Remove a variable form control to the form array "variables". This entry will no longer show up
   * in the list of variables for the user to modify/adjust settings for.
   *
   * @param index The index to remove from the "variables" form array.
   */
  removeVariable(index: number) {
    const formVariables = this.mlModelForm.get('variables') as UntypedFormArray;
    formVariables.removeAt(index);
    this.refreshVariables();
  }

  /**
   * Get variables (feature, label, and other options) from GA4 Events and First Party tables in BigQuery.
   */
  async fetchVariables() {
    let variables: Variable[] = this.cachedVariables;

    this.fetchingVariables = true;
    if (this.variableRequirementsProvided) {
      try {
        const input = this.value('input');
        const dataset = this.value('bigQueryDataset');
        const ts = this.value('timespans');
        variables = await this.mlModelsService.getVariables(input, dataset, ts);
        this.cachedVariables = variables;
        this.errorMessage = '';
        this.refreshVariables();
      } catch (error) {
        this.errorMessage = error || 'An error occurred';
      }
    }
    this.fetchingVariables = false;
  }

  /**
   * Get variables from cache, filtering where necessary, and specifically
   * returning a copy to keep cache in original state.
   */
  getVariables(): Variable[] {
    const includesFirstPartyData: boolean = this.input.source.includes(Source.FIRST_PARTY);
    let variables: Variable[] = this.copy(this.cachedVariables);

    if (!includesFirstPartyData) {
      return variables.filter(v => v.source !== Source.FIRST_PARTY);
    }
    return variables as Variable[];
  }

  /**
   * Attaches existing variable configuration for a model to the form.
   * Updates variable form fields based on related/linked form field changes.
   */
  refreshVariables() {
    const formVariables: Variable[] = this.value('variables');
    const existingVariables: Variable[] = (formVariables.length ? formVariables : this.mlModel.variables) || [];
    const variables: Variable[] = this.getVariables();
    const variableSources: string[] = variables.map(v => v.source).filter((s, i, a) => a.indexOf(s) === i);
    const isRegressionModel: boolean = this.type.isRegression;
    const comparisons = Object.keys(Comparison).map(c => {
      return { value: Comparison[c], label: c };
    });

    if (!existingVariables.length) {
      this.addVariable();
      return;
    }

    let controls = [];

    for (let existingVariable of existingVariables) {
      const matchingVariables = variables.filter(v => v.source === existingVariable.source);
      if (!matchingVariables.length) {
        continue;
      }

      let variable = matchingVariables.find(v => v.name === existingVariable.name);
      if (!variable) {
        controls.push(this._fb.group({
          sources: [variableSources],
          source: [existingVariable.source],
          list: [variables.filter(v => v.source === existingVariable.source).map(v => { return {name: v.name, count: v.count} })],
          name: [null],
        }));
        continue;
      }

      variable.roles = this.getApplicableVariableRoles(existingVariables, variable);
      variable.role = existingVariable && variable.roles.includes(existingVariable.role) ? existingVariable.role : null;
      variable.comparisons = null;
      variable.comparison = null;
      variable.value = null;
      variable.key = null;
      variable.key_required = false;
      variable.hint = null;

      if (existingVariable && existingVariable.key && variable.role) {
        variable.key = existingVariable.key;
        variable.value_type = variable.parameters.find(p => p.key === variable.key).value_type;
      }

      if (variable.role === Role.FEATURE && variable.source === Source.GOOGLE_ANALYTICS) {
        variable.comparisons = comparisons;
        variable.key_required = false;
        if (variable.key && existingVariable) {
          variable.comparison = existingVariable.comparison;
          variable.value = existingVariable.value;
        }
        variable.hint = 'When no key is selected the feature value will be the event count for a given user.';
      }

      if (variable.role === Role.LABEL && variable.source === Source.GOOGLE_ANALYTICS) {
        variable.key_required = true;
        variable.hint = `${isRegressionModel ? 'First value' : 'Trigger event'} will be automatically derived from the first occurrence of this event if not assigned.`;
      }

      if ([Role.FIRST_VALUE, Role.TRIGGER_EVENT].includes(variable.role) && variable.source === Source.GOOGLE_ANALYTICS) {
        variable.key_required = true;
        variable.hint = 'Trigger date will be automatically derived from the first date associated with this event.';
      }

      if (variable.role === Role.GCLID) {
        variable.hint = 'Trigger date field will be used as the datetime for the conversion sent to Google Ads.';
      }

      const control = this._fb.group({
        sources: [variableSources],
        source: [variable.source, this.enumValidator(Source)],
        list: [variables.filter(v => v.source === existingVariable.source).map(v => { return {name: v.name, count: v.count} })],
        name: [variable.name],
        key_placeholder: 'Key' + (variable.key_required ? ' *' : ''),
        roles: [variable.roles],
        role: [variable.role, this.enumValidator(Role)],
        parameters: [variable.key_required || variable.comparisons ? variable.parameters : null],
        key: [
          variable.key,
          variable.key_required ? [Validators.required] : []
        ],
        comparisons: [variable.comparisons],
        comparison: [variable.comparison, this.enumValidator(Comparison)],
        value: [variable.value],
        value_type: [variable.value_type],
        hint: variable.hint
      });

      control.setValidators(this.variableValidator(existingVariables));
      controls.push(control);
    }

    this.mlModelForm.setControl('variables', this._fb.array(controls));
  }

  /**
   * Get variable roles based on set form parameters and variable source.
   *
   * @param existingVariables The list of variables already assigned a role in the form.
   * @param variable The variable for which the roles will be assigned (used to filter specific roles).
   * @returns The list of roles that should be available for selection.
   */
  getApplicableVariableRoles(existingVariables: Variable[], variable: Variable): Role[] {
    let roles: Role[] = Object.values(Role);
    const uniqueId: UniqueId = this.value('uniqueId');
    const source: Source = this.value('input', 'source');
    const destination: Destination = this.value('output', 'destination');
    const isRegressionModel: boolean = this.type.isRegression;
    const isClassificationModel: boolean = this.type.isClassification;

    if (variable.source === Source.FIRST_PARTY) {
      roles = roles.filter(r =>
        ![Role.TRIGGER_EVENT].includes(r)
      );

      if (uniqueId == UniqueId.CLIENT_ID) {
        roles = roles.filter(r => r !== Role.USER_ID);
      } else if (uniqueId == UniqueId.USER_ID) {
        roles = roles.filter(r => r !== Role.CLIENT_ID);
      }

      const triggerDateDerived: Variable = existingVariables?.find(v =>
        v.source === Source.GOOGLE_ANALYTICS && [Role.FIRST_VALUE, Role.TRIGGER_EVENT].includes(v.role)
      );
      if (triggerDateDerived) {
        roles = roles.filter(r => r !== Role.TRIGGER_DATE);
      }

      if ((destination && destination !== Destination.GOOGLE_ADS_OFFLINE_CONVERSION) || source.includes(Source.GOOGLE_ANALYTICS)) {
        roles = roles.filter(r => r !== Role.GCLID);
      }
    } else if (variable.source === Source.GOOGLE_ANALYTICS) {
      roles = roles.filter(r =>
        ![Role.TRIGGER_DATE, Role.CLIENT_ID, Role.USER_ID, Role.GCLID].includes(r)
      );
    }

    if (isRegressionModel) {
      roles = roles.filter(r => r !== Role.TRIGGER_EVENT);
    } else if (isClassificationModel) {
      roles = roles.filter(r => r !== Role.FIRST_VALUE);
    }

    return roles;
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
   * Attaches existing hyper parameter configuration for a model to the form.
   * Updates hyper parameter form fields based on related/linked form field changes.
   */
  refreshHyperParameters() {
    const formHyperParameters = this.value('hyperParameters');
    const modelType: Type = this.value('type');
    const existingParams = formHyperParameters.length ? formHyperParameters : this.mlModel.hyper_parameters;
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
   * Attaches existing timespan configuration for a model to the form.
   */
  refreshTimespans() {
    const existingTimespans: Timespan[] = this.mlModel.timespans;
    const timespans: Timespan[] = MlModel.getDefaultTimespans();
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
   * Dynamically updates required output parameters based on the output destination selected.
   */
  refreshOutput() {
    const output: Output = this.output;
    const allRequirementsFields: string[] = Object.keys(output.parameters);

    for (const requirement of allRequirementsFields) {
      const field = this.mlModelForm.get(['output', 'parameters', requirement]);
      if (output.requirements.includes(requirement)) {
        field.addValidators(Validators.required);
      } else {
        field.removeValidators(Validators.required);
        field.setValue(null);
      }
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
    this.mlModel.input = {
      source: formModel.input.source as string,
      parameters: {
        google_analytics_project: formModel.input.parameters.googleAnalyticsProject as string,
        google_analytics_dataset: formModel.input.parameters.googleAnalyticsDataset as string,
        first_party_project: formModel.input.parameters.firstPartyProject as string,
        first_party_dataset: formModel.input.parameters.firstPartyDataset as string,
        first_party_table: formModel.input.parameters.firstPartyTable as string
      }
    } as Input;
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
    this.state = State.LOADING;
    this.prepareSaveMlModel();

    try {
      if (this.mlModel.id) {
        await this.mlModelsService.update(this.mlModel);
        this.router.navigate(['ml-models', this.mlModel.id]);
      } else {
        const mlModel = await this.mlModelsService.create(this.mlModel)
        this.router.navigate(['ml-models', mlModel.id]);
      }
      this.errorMessage = '';
    } catch (error) {
      this.errorMessage = error || 'An error occurred';
    }

    this.state = State.LOADED;
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

  /**
   * Validate variable based a complex set of requirements.
   *
   * @param existingVariables The existing variables (what's currently set in the form).
   * @returns Any error that resulted from a requirement check step.
   */
  private variableValidator(existingVariables: Variable[]): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const variableRole: Role = control.get('role').value;

      if (variableRole) {
        if (variableRole !== Role.FEATURE) {
          const variablesWithRole = existingVariables.filter(v => v.role === variableRole);
          if (variablesWithRole.length > 1) {
            return {cannotAssignThisRoleToMultipleVariables: true};
          }
        } else {
          const key = control.get('key').value;
          const comparison = control.get('comparison').value;
          const value = control.get('value').value;

          if (key && !comparison) {
            return {comparisonRequiredWhenKeySelected: true}
          }

          if (comparison && !value) {
            return {valueRequiredForComparison: true}
          }
        }
      }

      return null;
    }
  }

  /**
   * Check if the minimum number of features is specified.
   *
   * @param variables The currently configured/selected variables.
   * @param errors A running list of errors found during check calls.
   */
  private checkMinimumNumberOfFeatures(variables: Variable[], errors: string[]) {
    if (variables.filter(v => v.role === Role.FEATURE).length < MIN_NUM_OF_FEATURES) {
      errors.push(`At least ${MIN_NUM_OF_FEATURES} features must be selected/specified.`);
    }
  }

  /**
   * Check if one and only one label is specified.
   *
   * @param variables The currently configured/selected variables.
   * @param errors A running list of errors found during check calls.
   */
  private checkOneLabel(variables: Variable[], errors: string[]) {
    if (variables.filter(v => v.role === Role.LABEL).length === 0) {
      errors.push('A label must be selected/specified.');
    } else if (variables.filter(v => v.role === Role.LABEL).length > 1) {
      errors.push('Only 1 label can be selected/specified.');
    }
  }

  /**
   * Check if proper unique identifier is specified.
   *
   * @param variables The currently configured/selected variables.
   * @param errors A running list of errors found during check calls.
   */
  private checkUniqueId(variables: Variable[], errors: string[]) {
    const uniqueId: UniqueId = this.value('uniqueId');

    if (uniqueId === UniqueId.CLIENT_ID && variables.filter(v => v.role === Role.CLIENT_ID).length === 0) {
      errors.push('A client ID must be selected/specified due to it being selected as the user identifier.');
    }

    if (uniqueId === UniqueId.USER_ID && variables.filter(v => v.role === Role.USER_ID).length === 0) {
      errors.push('A user ID must be selected/specified due to it being selected as the user identifier.');
    }
  }

  /**
   * Check if GCLID provided when Google Ads is set as the destination
   * if the GCLID cannot be pulled automatically from Google Analytics.
   *
   * @param variables The currently configured/selected variables.
   * @param errors A running list of errors found during check calls.
   */
  private checkGCLID(variables: Variable[], errors: string[]) {
    const source: Source = this.value('input', 'source');
    const destination: Destination = this.value('output', 'destination');
    const selectedGCLID: Variable = variables.find(v => v.role === Role.GCLID);

    if (!source.includes(Source.GOOGLE_ANALYTICS) && destination === Destination.GOOGLE_ADS_OFFLINE_CONVERSION && !selectedGCLID) {
      errors.push('A GCLID must be selected/specified due to the specified destination and no way to automatically derive.');
    }
  }

  /**
   * Check if possible to derive trigger date from Google Analytics variables
   * that were selected and if not then add error to the errors list.
   *
   * @param variables The currently configured/selected variables.
   * @param errors A running list of errors found during check calls.
   */
  private checkTriggerDate(variables: Variable[], errors: string[]) {
    const selectedTriggerDate: Variable = variables.find(v => v.role === Role.TRIGGER_DATE);

    if (!selectedTriggerDate) {
      const source: Source = this.value('input', 'source');
      const selectedTrigger: Variable = variables.find(v => [Role.FIRST_VALUE, Role.TRIGGER_EVENT].includes(v.role));
      const selectedLabel = variables.find(v => v.role === Role.LABEL);

      if (
        !source.includes(Source.GOOGLE_ANALYTICS) ||
        (!selectedTrigger && selectedLabel && selectedLabel.source !== Source.GOOGLE_ANALYTICS) ||
        (selectedTrigger && selectedTrigger.source === Source.FIRST_PARTY)
      ) {
        errors.push('A trigger date must be selected/specified due to there being no way to automatically derive.');
      }
    }
  }

  /**
   * Return a deep copy of anything passed to it.
   *
   * @param item The thing to copy.
   * @returns The copy.
   */
  private copy(item: any): any {
    return JSON.parse(JSON.stringify(item));
  }
}
