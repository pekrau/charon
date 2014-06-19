" Charon: initialize for tests using nosetest. "

import os
import json

import requests
from nose import with_setup

from charon import settings
from charon import utils

utils.load_settings(filepath=os.getenv('SETTINGS'))

# This key is associated with a user account, and must be current.
apikey = {'X-Charon-API-key': settings['TEST_API_KEY']}

# Speed improvement: reuse open connection, rather than create new every time
session = requests.Session()

def url(*segments):
    "Synthesize absolute URL from path segments."
    return "{0}api/v1/{1}".format(settings['BASE_URL'],
                                  '/'.join([str(s) for s in segments]))
