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

from oauthlib import oauth2
import urllib2

# The AdWords API OAuth 2.0 scope
SCOPE = u'https://adwords.google.com/api/adwords'
# This callback URL will allow you to copy the token from the success screen
CALLBACK_URL = 'urn:ietf:wg:oauth:2.0:oob'
# The web address for generating new OAuth 2.0 credentials (endpoints in
# OAuth 2 are targets with a specific responsibility)
GOOGLE_OAUTH2_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_OAUTH2_GEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
HTTPS_PROXY = None
# The HTTP headers needed on OAuth 2.0 refresh requests
OAUTH2_REFRESH_HEADERS = {
    'content-type': 'application/x-www-form-urlencoded'}


def get_url(client_id):
  oauthlib_client = oauth2.WebApplicationClient(client_id)
  # This is the URL construction for getting the authorisation code
  authorize_url = oauthlib_client.prepare_request_uri(
      GOOGLE_OAUTH2_AUTH_ENDPOINT, redirect_uri=CALLBACK_URL, scope=SCOPE)

  return authorize_url


def get_token(client_id, client_secret, ads_code):
  oauthlib_client = oauth2.WebApplicationClient(client_id)
  # Prepare the access token request body --> makes a
  # request to the token endpoint by adding the following parameters
  post_body = oauthlib_client.prepare_request_body(
      client_secret=client_secret, code=ads_code, redirect_uri=CALLBACK_URL)
  # URL request
  request = urllib2.Request(GOOGLE_OAUTH2_GEN_ENDPOINT,
                            post_body, OAUTH2_REFRESH_HEADERS)
  if HTTPS_PROXY:
    request.set_proxy(HTTPS_PROXY, 'https')
  # Open the given url, read and decode into raw_response
  raw_response = urllib2.urlopen(request).read().decode()
  # Parse the JSON response body given in raw_response
  oauth2_credentials = oauthlib_client.parse_request_body_response(
      raw_response)
  # Return the refresh token
  token = oauth2_credentials['refresh_token']

  return token
