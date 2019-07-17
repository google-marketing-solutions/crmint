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

from flask import Blueprint
from flask_restful import Resource, fields, marshal_with, reqparse

from core.models import Param, GeneralSetting
from core.app_data import SA_DATA
from ibackend.extensions import api
from google.appengine.api import urlfetch
#from core import models
#added two libraries
import urllib2
# giving error: No module named oauthlib
from oauthlib import oauth2

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
    #added value
    'google_ads_auth_url': fields.String,
}

global_variables_fields = {
    'variables': fields.List(fields.Nested(param_fields)),
}


class Configuration(Resource):

  @marshal_with(configuration_fields)
  def get(self):
    print('doing get')
    urlfetch.set_default_fetch_deadline(300)
    params = Param.where(pipeline_id=None, job_id=None).order_by(Param.name)
    settings = GeneralSetting.query.order_by(GeneralSetting.name)

    # Get client id and secret from input fields stored in database
    CLIENT_ID = GeneralSetting.where(name='client_id').first().value
    # The AdWords API OAuth 2.0 scope
    SCOPE = u'https://adwords.google.com/api/adwords'
    # This callback URL will allow you to copy the token from the success screen
    CALLBACK_URL = 'urn:ietf:wg:oauth:2.0:oob'
    # The web address for generating new OAuth 2.0 credentials (endpoints in
    #OAuth 2 are targets with a specific responsibility)
    GOOGLE_OAUTH2_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'

    oauthlib_client = oauth2.WebApplicationClient(CLIENT_ID)
    # This is the URL construction for getting the authorisation code
    authorize_url = oauthlib_client.prepare_request_uri(
      GOOGLE_OAUTH2_AUTH_ENDPOINT, redirect_uri=CALLBACK_URL, scope=SCOPE)

    # url to redirect
    url = authorize_url

    return {
        "sa_email": SA_DATA['client_email'],
        "variables": params,
        "settings": settings,
        #added url to config
        "google_ads_auth_url": url,
    }



class GlobalVariable(Resource):

  @marshal_with(global_variables_fields)
  def put(self):
    args = parser.parse_args()
    Param.update_list(args.get('variables'))
    print('put 1')
    return {
        "variables": Param.where(pipeline_id=None, job_id=None).all()
    }


class GeneralSettingsRoute(Resource):

  @marshal_with(settings_fields)
  def put(self):
    args = settings_parser.parse_args()
    print(args)
    # Get client id and secret from input fields stored in database
    CLIENT_ID = GeneralSetting.where(name='client_id').first().value
    CLIENT_SECRET = GeneralSetting.where(name='client_secret').first().value
    HTTPS_PROXY = None
    # This callback URL will allow you to copy the token from the success screen
    CALLBACK_URL = 'urn:ietf:wg:oauth:2.0:oob'
    # The HTTP headers needed on OAuth 2.0 refresh requests
    OAUTH2_REFRESH_HEADERS = {'content-type':
      'application/x-www-form-urlencoded'}
    # The web address for generating new OAuth 2.0 credentials (endpoints in OAuth 2 are targets with a specific responsibility)
    GOOGLE_OAUTH2_GEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'

    oauthlib_client = oauth2.WebApplicationClient(CLIENT_ID)

    # This gets the value from the google_ads_authentication_code field
    #adsCode = GeneralSetting.where(name='google_ads_authentication_code').first().value
    ads_Code = [d['value'] for d in args['settings'] if d['name'] ==
      'google_ads_authentication_code'][0]
    print(ads_Code)

    token = ''

    print('Entering try')
    # Prepare the access token request body --> makes a request to the token endpoint by adding the following parameters
    post_body = oauthlib_client.prepare_request_body(client_secret=CLIENT_SECRET,
      code=ads_Code, redirect_uri=CALLBACK_URL)
    # URL request
    request = urllib2.Request(GOOGLE_OAUTH2_GEN_ENDPOINT,
      post_body, OAUTH2_REFRESH_HEADERS)
    print('request done')
    print(request)
    if HTTPS_PROXY:
      request.set_proxy(HTTPS_PROXY, 'https')
    # Open the given url, read and decode into raw_response
    raw_response = urllib2.urlopen(request).read().decode()
    print(raw_response)
    print('response')
    # Parse the JSON response body given in raw_response
    oauth2_credentials = oauthlib_client.parse_request_body_response(
      raw_response)
    # Return the refresh token
    token = oauth2_credentials['refresh_token']
    print(token)


    # Set the  value into the database
    #GeneralSetting.where(name='google_ads_refresh_token').first().value = token
    settings = []
    print('put 2')
    for arg in args['settings']:
     setting = GeneralSetting.where(name=arg['name']).first()
     print(setting)
     if setting:
       if setting.name == 'google_ads_refresh_token':
         setting.update(value=token)
       else:
         setting.update(value=arg['value'])
     settings.append(setting)


    return settings


api.add_resource(Configuration, '/configuration')
api.add_resource(GlobalVariable, '/global_variables')
api.add_resource(GeneralSettingsRoute, '/general_settings')
