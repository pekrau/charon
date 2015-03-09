""" Charon: nosetests /api/v1/libprep 
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
LIBPREPID = 'A'
LIBPREPID2 = 'B'

api_token = {'X-Charon-API-token': API_TOKEN}
session = requests.Session()


def my_setup():
    "Create the project and sample to work with libprep."
    data = dict(projectid=PROJECTID)
    session.post(url('project'), data=json.dumps(data), headers=api_token)
    data = dict(sampleid=SAMPLEID)
    session.post(url('sample', PROJECTID),
                 data=json.dumps(data),
                 headers=api_token)

def my_teardown():
    "Delete the project and all its dependents."
    session.delete(url('project', PROJECTID), headers=api_token)

@nose.with_setup(my_setup, my_teardown)
def test_libprep_create():
    "Create a libprep."
    data = dict(libprepid=LIBPREPID, status="NEW")
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response.reason
    libprep = response.json()
    assert libprep['projectid'] == PROJECTID
    assert libprep['sampleid'] == SAMPLEID
    assert libprep['libprepid'] == LIBPREPID

@nose.with_setup(my_setup, my_teardown)
def test_librep_delete():
    data = dict(libprepid=LIBPREPID, status='NEW')
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    
    assert response.status_code == 201, response.reason
    libprep_url = BASE_URL.rstrip('/') + response.headers['location']
    response=session.delete(libprep_url, headers=api_token)
    assert response.status_code == 204, response.reason 
@nose.with_setup(my_setup, my_teardown)
def test_libprep_modify():
    "Create and modify a libprep."
    # Create the libprep, with status 'new'
    data = dict(libprepid=LIBPREPID, qc='PASSED')
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response.reason
    libprep = response.json()
    assert libprep['projectid'] == PROJECTID
    assert libprep['sampleid'] == SAMPLEID
    assert libprep['libprepid'] == LIBPREPID
    assert libprep['qc'] == 'PASSED'
    libprep_url = BASE_URL.rstrip('/') + response.headers['location']
    # Modify the libprep, setting status to 'aborted'
    data = dict(qc='FAILED')
    response = session.put(libprep_url,
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response.reason
    response = session.get(libprep_url, headers=api_token)
    assert response.status_code == 200, response.reason
    libprep = response.json()
    assert libprep['qc'] == 'FAILED'
    # Try setting an invalid status
    data = dict(qc='no-such-status')
    response = session.put(libprep_url,
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 400, response.reason

@nose.with_setup(my_setup, my_teardown)
def test_libprep_create_collision():
    "Create a libprep, and try creating another with same name."
    data = dict(libprepid=LIBPREPID)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response.reason
    libprep = response.json()
    assert libprep['projectid'] == PROJECTID
    assert libprep['sampleid'] == SAMPLEID
    assert libprep['libprepid'] == LIBPREPID
    data = dict(libprepid=LIBPREPID)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 400, response.reason

@nose.with_setup(my_setup, my_teardown)
def test_libprep_create_multiple():
    "Create several libpreps, obtain list of all."
    data = dict(libprepid=LIBPREPID)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response.reason
    libprep = response.json()
    assert libprep['projectid'] == PROJECTID
    assert libprep['sampleid'] == SAMPLEID
    assert libprep['libprepid'] == LIBPREPID
    data = dict(libprepid=LIBPREPID2)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response.reason
    libprep2 = response.json()
    assert libprep2['projectid'] == PROJECTID
    assert libprep2['sampleid'] == SAMPLEID
    assert libprep2['libprepid'] == LIBPREPID2
    assert libprep['_id'] != libprep2['_id']
    response = session.get(url('libpreps', PROJECTID, SAMPLEID),
                           headers=api_token)
    assert response.status_code == 200, response.reason
    data = response.json()
    assert 'libpreps' in data
    assert len(data['libpreps']) == 2
