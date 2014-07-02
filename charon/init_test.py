" Charon: initialize for tests using nosetest. "

import os
import json

import requests
from nose import with_setup


# NOTE: Load of settings is needed *only* to get the test API token
# and the base URL. Those value can in principle be set by
# some other mechanism, e.g. from environment variables.
# No other Charon package settings are used by the test scripts.
from charon import utils
settings = utils.load_settings(filepath=os.getenv('CHARON_SETTINGS'))
TEST_API_TOKEN = settings['TEST_API_TOKEN']
BASE_URL = settings['BASE_URL']

# This token is associated with a user account, and must be current.
api_token = {'X-Charon-API-token': TEST_API_TOKEN}

# Optimize speed: reuse open connection, rather than create new every time
session = requests.Session()

def url(*segments):
    "Synthesize absolute URL from path segments."
    return "{0}api/v1/{1}".format(BASE_URL,'/'.join([str(s) for s in segments]))
