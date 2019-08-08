# Copyright 2018 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""General section."""

from core.app_data import SA_DATA
from core.models import Param, GeneralSetting
from flask import Blueprint
from flask_restful import Resource, fields, marshal_with, reqparse
from ibackend.extensions import api
import ads_auth_code

from google.appengine.api import urlfetch

blueprint = Blueprint('general', __name__)

parser = reqparse.RequestParser()
parser.add_argument('variables', type=list, location='json')

settings_parser = reqparse.RequestParser()
settings_parser.add_argument('settings', type=list, location='json')

param_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'type': fields.String,
    'value': fields.Raw(attribute='api_value'),
}

setting_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'value': fields.String,
}

settings_fields = {
    'settings': fields.List(fields.Nested(setting_fields)),
}

configuration_fields = {
    'sa_email': fields.String,
    'variables': fields.List(fields.Nested(param_fields)),
    'settings': fields.List(fields.Nested(setting_fields)),
    # Added value
    'google_ads_auth_url': fields.String,
}

global_variables_fields = {
    'variables': fields.List(fields.Nested(param_fields)),
}


class Configuration(Resource):

  @marshal_with(configuration_fields)
  def get(self):
    urlfetch.set_default_fetch_deadline(300)
    params = Param.where(pipeline_id=None, job_id=None).order_by(Param.name)
    settings = GeneralSetting.query.order_by(GeneralSetting.name)

    # Get client id and secret from input fields stored in database
    client_id = GeneralSetting.where(name='client_id').first().value
    # Url to redirect
    url = ads_auth_code.get_url(client_id)

    return {
        'sa_email': SA_DATA['client_email'],
        'variables': params,
        'settings': settings,
        # Added url to config
        'google_ads_auth_url': url,
    }


class GlobalVariable(Resource):

  @marshal_with(global_variables_fields)
  def put(self):
    args = parser.parse_args()
    Param.update_list(args.get('variables'))
    return {
        'variables': Param.where(pipeline_id=None, job_id=None).all()
    }


class GeneralSettingsRoute(Resource):

  @marshal_with(settings_fields)
  def put(self):
    args = settings_parser.parse_args()
    # Get client id and secret from input fields stored in database
    client_id = GeneralSetting.where(name='client_id').first().value
    client_secret = GeneralSetting.where(name='client_secret').first().value

    # Gets value from the google_ads_authentication_code field
    ads_code = [d['value'] for d in args['settings']
                if d['name'] == 'google_ads_authentication_code'][0]
    if ads_code:
        token = ads_auth_code.get_token(client_id, client_secret, ads_code)
    else:
        token = None

    settings = []
    for arg in args['settings']:
      setting = GeneralSetting.where(name=arg['name']).first()
      if setting:
        if setting.name == 'google_ads_refresh_token' and token:
          setting.update(value=token)
        elif setting.name == 'google_ads_authentication_code':
          setting.update(value='')
        else:
          setting.update(value=arg['value'])
      settings.append(setting)
    return settings

api.add_resource(Configuration, '/configuration')
api.add_resource(GlobalVariable, '/global_variables')
api.add_resource(GeneralSettingsRoute, '/general_settings')
