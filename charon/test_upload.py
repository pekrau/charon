""" Charon: nosetests /project/{projectid}/upload
Requires env vars CHARON_API_TOKEN and CHARON_BASE_URL.
"""

import os
import json
import requests
import nose

def url_direct(*segments):
    "Synthesize absolute URL from path segments. Not to API!"
    return "{0}{1}".format(BASE_URL, '/'.join([str(s) for s in segments]))

def url(*segments):
    "Synthesize absolute URL from path segments."
    return "{0}api/v1/{1}".format(BASE_URL,'/'.join([str(s) for s in segments]))

API_TOKEN = os.getenv('CHARON_API_TOKEN')
if not API_TOKEN: raise ValueError('no API token')
BASE_URL = os.getenv('CHARON_BASE_URL')
if not BASE_URL: raise ValueError('no base URL')

api_token = {'X-Charon-API-token': API_TOKEN}
session = requests.Session()


PROJECTID = 'P0'

NEW_SAMPLES = """S1
S2
S23
"""

def my_setup():
    "Create the project to work with samples."
    data = dict(projectid=PROJECTID)
    session.post(url('project'), data=json.dumps(data), headers=api_token)

def my_teardown():
    "Delete the project and all its dependents."
    session.delete(url('project', PROJECTID), headers=api_token)

@nose.with_setup(my_setup, my_teardown)
def test_upload_project_new_samples():
    "Upload a CSV file with new samples. NOTE: Use POST to project API URL."
    # Add new samples
    files = dict(csvfile=('new_samples.csv', NEW_SAMPLES))
    response = session.post(url('project', PROJECTID),
                            files=files,
                            headers=api_token)
    assert response.status_code == 200, response
    # Sample exists?
    response = session.get(url('sample', PROJECTID, 'S2'), headers=api_token)
    assert response.status_code == 200, response
    # Sample should not exist?
    response = session.get(url('sample', PROJECTID, 'S123'), headers=api_token)
    assert response.status_code == 404, response
    # Try adding existing samples
    response = session.post(url('project', PROJECTID),
                            files=files,
                            headers=api_token)
    assert response.status_code == 400, response
