""" Charon: nosetests /api/v1/sample 
Requires env vars CHARON_API_TOKEN and CHARON_BASE_URL.
"""

import os
import json
import requests
import nose

def url(*segments):
    "Synthesize absolute URL from path segments."
    return "{0}api/v1/{1}".format(BASE_URL,'/'.join([str(s) for s in segments]))

API_TOKEN = os.getenv('CHARON_API_TOKEN')
if not API_TOKEN: raise ValueError('no API token')
BASE_URL = os.getenv('CHARON_BASE_URL')
if not BASE_URL: raise ValueError('no base URL')

PROJECTID = 'P0'
SAMPLEID = 'S1'

api_token = {'X-Charon-API-token': API_TOKEN}
session = requests.Session()


def my_setup():
    "Create the project to work with samples."
    data = dict(projectid=PROJECTID)
    session.post(url('project'), data=json.dumps(data), headers=api_token)

def my_teardown():
    "Delete the project and all its dependents."
    session.delete(url('project', PROJECTID), headers=api_token)

@nose.with_setup(my_setup, my_teardown)
def test_sample_deletion():
    data = dict(sampleid=SAMPLEID)
    response = session.post(url('sample', PROJECTID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    sample_url = BASE_URL.rstrip('/') + response.headers['location']
    response = session.delete(sample_url,
                           headers=api_token)
    assert response.status_code == 204 

@nose.with_setup(my_setup, my_teardown)
def test_sample_create():
    "Create a sample."
    data = dict(sampleid=SAMPLEID)
    response = session.post(url('sample', PROJECTID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    sample = response.json()
    assert sample['projectid'] == PROJECTID
    assert sample['sampleid'] == SAMPLEID

@nose.with_setup(my_setup, my_teardown)
def test_sample_modify():
    "Create and modify a sample."
    data = dict(sampleid=SAMPLEID, status='NEW')
    response = session.post(url('sample', PROJECTID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response.reason
    sample = response.json()
    assert sample['projectid'] == PROJECTID
    assert sample['sampleid'] == SAMPLEID
    assert sample['status'] == 'NEW'
    sample_url = BASE_URL.rstrip('/') + response.headers['location']
    data = dict(status='DATA_FAILED')
    response = session.put(sample_url,
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(sample_url, headers=api_token)
    assert response.status_code == 200, response
    sample = response.json()
    assert sample['status'] == 'DATA_FAILED'
    data = dict(status='no-such-value')
    response = session.put(sample_url,
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 400, response

@nose.with_setup(my_setup, my_teardown)
def test_no_such_sample():
    "Access a non-existing sample."
    response = session.get(url('sample', PROJECTID, 'no such sample'),
                           headers=api_token)
    assert response.status_code == 404

@nose.with_setup(my_setup, my_teardown)
def test_sample_create_collision():
    "Create a sample, and try creating another with same name."
    data = dict(sampleid=SAMPLEID)
    response = session.post(url('sample', PROJECTID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    sample = response.json()
    assert sample['projectid'] == PROJECTID
    assert sample['sampleid'] == SAMPLEID
    data = dict(sampleid=SAMPLEID)
    response = session.post(url('sample', PROJECTID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 400, response
