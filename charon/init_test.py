" Charon: initialize for tests using nosetest. "

import os
import json

import requests
from nose import with_setup


# NOTE: This is needed *only* to get the test API token.
# No other Charon package settings are used by the test scripts.
from charon import settings
from charon import utils
utils.load_settings(filepath=os.getenv('SETTINGS'))

# This token is associated with a user account, and must be current.
api_token = {'X-Charon-API-token': settings['TEST_API_TOKEN']}

# Optimize speed: reuse open connection, rather than create new every time
session = requests.Session()

def url(*segments):
    "Synthesize absolute URL from path segments."
    return "{0}api/v1/{1}".format(settings['BASE_URL'],
                                  '/'.join([str(s) for s in segments]))
