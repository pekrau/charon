""" Charon: nosetests /api/v1/version
Requires env vars CHARON_API_TOKEN and CHARON_BASE_URL.
"""

import os
import requests

def url(*segments):
    "Synthesize absolute URL from path segments."
    return "{0}api/v1/{1}".format(BASE_URL,'/'.join([str(s) for s in segments]))

API_TOKEN = os.getenv('CHARON_API_TOKEN')
if not API_TOKEN: raise ValueError('no API token')
BASE_URL = os.getenv('CHARON_BASE_URL')
if not BASE_URL: raise ValueError('no base URL')

api_token = {'X-Charon-API-token': API_TOKEN}
session = requests.Session()


def test_version():
    "Access version with header carrying API token."
    response = session.get(url('version'), headers=api_token)
    assert response.status_code == requests.codes.ok
    data = response.json()
    assert 'Charon' in data

def test_version_no_header():
    "No access without header carrying API token."
    response = session.get(url('version'))
    assert response.status_code == 401
