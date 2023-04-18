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

import { Component, OnInit } from '@angular/core';
import { UntypedFormGroup, UntypedFormArray, UntypedFormBuilder, Validators } from '@angular/forms';

import { plainToClass } from 'class-transformer';

import { SettingsService } from './shared/settings.service';
import { Config, Setting } from '../config';
import { Param } from 'app/models/param';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.sass'],
  providers: [SettingsService]
})
export class SettingsComponent implements OnInit {
  config: Config = {
    sa_email: 'Unknown',
    settings: [],
    variables: [],
    google_ads_auth_url: '',
  };

  resetStatusesRunning = false;

  gVarsForm: UntypedFormGroup;
  settingsForm: UntypedFormGroup;
  googleAdsAuthURL: string;

  constructor(
    private settingsService: SettingsService,
    private _fb: UntypedFormBuilder
  ) { }

  ngOnInit() {
    this.createGVarsForm();
    this.createSettingsForm();
    this.settingsService.getConfigData()
                   .then(config => {
                     this.config = plainToClass(Config, config);
                     this.assignModelToSettingsForm();
                     this.assignModelToGVarsForm();
                   });
  }

  // --------------- GENERAL SETTINGS FORM ----------------
  createSettingsForm() {
    this.settingsForm = this._fb.group({
      settingsLairs: this._fb.array([])
    });
  }

  assignModelToSettingsForm() {
    this.settingsForm.reset({
      settingsLairs: this._fb.array([])
    });
    this.setSettingsLairs(this.config.settings);
    //setting values for google url
    this.googleAdsAuthURL = this.config.google_ads_auth_url;
  }

  setSettingsLairs(settings) {
    const setting_fgs = settings.map(setting => this._fb.group(setting));
    this.settingsForm.setControl('settingsLairs', this._fb.array(setting_fgs));
  }

  get settingsLairs(): UntypedFormArray {
    return this.settingsForm.get('settingsLairs') as UntypedFormArray;
  }

  prepareSaveSettings() {
    const formModel = this.settingsForm.value;

    // deep copy of form model lairs
    const settingsDeepCopy: Setting[] = formModel.settingsLairs.map(
      (setting: Setting) => Object.assign({}, setting)
    );

    this.config.settings = settingsDeepCopy;
  }

  saveSettings() {
    this.prepareSaveSettings();

    this.settingsService.saveSettings(this.config.settings);
  }

  // --------------- END GENERAL SETTINGS FORM ------------

  // --------------- GLOBAL VARIABLES FORM ----------------
  createGVarsForm() {
    this.gVarsForm = this._fb.group({
      variablesLairs: this._fb.array([])
    });
  }

  assignModelToGVarsForm() {
    this.gVarsForm.reset({
      variablesLairs: this._fb.array([])
    });
    this.setVariablesLairs(this.config.variables);
  }

  setVariablesLairs(params: Param[]) {
    const param_fgs = params.map(param => this._fb.group(param));
    this.gVarsForm.setControl('variablesLairs', this._fb.array(param_fgs));
  }

  get variablesLairs(): UntypedFormArray {
    return this.gVarsForm.get('variablesLairs') as UntypedFormArray;
  }

  removeGVar(i: number) {
    // NOTE: code below does not work correctly.
    // const control = <FormArray>this.gVarsForm.controls['variablesLairs'];
    // control.removeAt(i);

    this.prepareSaveGVars();
    this.config.variables.splice(i, 1);
    this.setVariablesLairs(this.config.variables);
  }

  initGVar() {
      return this._fb.group({
          name: ['', [Validators.required, Validators.pattern('[a-zA-Z_][a-zA-Z0-9_]*')]],
          type: ['text'],
          value: ['']
      });
  }

  addGVar() {
    const control = <UntypedFormArray>this.gVarsForm.controls['variablesLairs'];
    control.push(this.initGVar());
  }

  prepareSaveGVars() {
    const formModel = this.gVarsForm.value;

    // deep copy of form model lairs
    const variablesDeepCopy: Param[] = formModel.variablesLairs.map(
      (variable: Param) => Object.assign({}, variable)
    );

    this.config.variables = variablesDeepCopy;
  }

  saveGVars() {
    this.prepareSaveGVars();

    this.settingsService.saveVariables(this.config.variables);
  }

  // --------------- END GLOBAL VARIABLES FORM ----------------

  resetStatuses() {
    this.resetStatusesRunning = true;
    this.settingsService.resetStatuses(() => {
      this.resetStatusesRunning = false;
    });
  }

  resetStatusesIsRunning(): boolean {
    return this.resetStatusesRunning;
  }
}
