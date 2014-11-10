""" Charon: nosetests /api/v1/seqrun 
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
SEQRUNID='1337_WORLD'

api_token = {'X-Charon-API-token': API_TOKEN}
session = requests.Session()


def my_setup():
    "Create the project, sample and libprep to work with seqrun."
    data = dict(projectid=PROJECTID)
    session.post(url('project'), data=json.dumps(data), headers=api_token)
    data = dict(sampleid=SAMPLEID)
    session.post(url('sample', PROJECTID),
                 data=json.dumps(data),
                 headers=api_token)
    data = dict(libprepid=LIBPREPID)
    session.post(url('libprep', PROJECTID, SAMPLEID),
                 data=json.dumps(data),
                 headers=api_token)

def my_teardown():
    "Delete the project and all its dependents."
    session.delete(url('project', PROJECTID), headers=api_token)



@nose.with_setup(my_setup, my_teardown)
def test_create_seqrun():
    "Create a seqrun in a libprep and manipulate it."
    data = dict(sequencing_status='NEW', mean_autosomal_coverage=0.0, seqrunid=SEQRUNID)
    response = session.post(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response.reason
    data = response.json()
    assert data['projectid'] == PROJECTID
    assert data['sampleid'] == SAMPLEID
    assert data['libprepid'] == LIBPREPID
    assert data['seqrunid'] == SEQRUNID, repr(data['seqrunid'])
    response = session.get(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, SEQRUNID),
                           headers=api_token)
    assert response.status_code == 200, response
    assert data == response.json()
    data = dict(status='DONE',
                alignment_status='RUNNING',
                runid='123_xyz_qwerty')
    response = session.put(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, SEQRUNID),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, SEQRUNID),
                           headers=api_token)
    newdata = response.json()
    assert data['runid'] == newdata['runid']
    data = dict(status='DONE',
                alignment_status='DONE',
                mean_autosomal_coverage=1.0)
    response = session.put(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, SEQRUNID),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, SEQRUNID),
                           headers=api_token)
    newdata = response.json()
    assert data['mean_autosomal_coverage'] == newdata['mean_autosomal_coverage']

    data = dict(sequencing_status='NEW', mean_autosomal_coverage=0.0, seqrunid=SEQRUNID)
    response = session.post(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 400, response.reason

@nose.with_setup(my_setup, my_teardown)
def test_delete_seqrun():

    data = dict(sequencing_status='NEW', mean_autosomal_coverage=0.0, seqrunid=SEQRUNID)
    response = session.post(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response.reason
    seqrun_url= BASE_URL.rstrip('/') + response.headers['location']
    response = session.delete(seqrun_url, headers=api_token)
    assert response.status_code == 204, response.reason
