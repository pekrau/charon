" Charon: setup for tests using nosetest. "

import json

import requests
from nose import with_setup

from charon import settings

BASE_URL = settings['BASE_URL']
API_URL = BASE_URL + 'api/v1'

# This key is associated with a user account, and must be current.
apikey = {'X-Charon-API-key': settings['TEST_API_KEY']}

def url(*segments):
    "Synthesize absolute URL from path segments."
    return API_URL + '/' + '/'.join([str(s) for s in segments])
