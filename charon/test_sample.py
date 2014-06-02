" Charon: nosetests /api/v1/sample "

from charon.setup_test import *

PROJECTID = 'P0'
SAMPLEID = 'S1'


def my_setup():
    "Create the project to work with samples."
    data = dict(projectid=PROJECTID)
    requests.post(url('project'), data=json.dumps(data), headers=apikey)

def my_teardown():
    "Delete the project and all its dependents."
    requests.delete(url('project', PROJECTID), headers=apikey)

@with_setup(my_setup, my_teardown)
def test_sample_create():
    "Create a sample."
    data = dict(sampleid=SAMPLEID)
    response = requests.post(url('sample', PROJECTID),
                             data=json.dumps(data),
                             headers=apikey)
    assert response.status_code == 201, response
    sample = response.json()
    assert sample['projectid'] == PROJECTID
    assert sample['sampleid'] == SAMPLEID

@with_setup(my_setup, my_teardown)
def test_sample_modify():
    "Create and modify a sample."
    data = dict(sampleid=SAMPLEID, status='new')
    response = requests.post(url('sample', PROJECTID),
                             data=json.dumps(data),
                             headers=apikey)
    assert response.status_code == 201
    sample = response.json()
    assert sample['projectid'] == PROJECTID
    assert sample['sampleid'] == SAMPLEID
    assert sample['status'] == 'new'
    sample_url = HOST_URL + response.headers['location']
    data = dict(status='old')
    response = requests.put(sample_url,
                            data=json.dumps(data),
                            headers=apikey)
    assert response.status_code == 204, response
    response = requests.get(sample_url, headers=apikey)
    assert response.status_code == 200, response
    sample = response.json()
    assert sample['status'] == 'old'

@with_setup(my_setup, my_teardown)
def test_no_such_sample():
    "Access a non-existing sample."
    response = requests.get(url('sample', PROJECTID, 'no such sample'),
                            headers=apikey)
    assert response.status_code == 404

@with_setup(my_setup, my_teardown)
def test_sample_create_collision():
    "Create a sample, and try creating another with same name."
    data = dict(sampleid=SAMPLEID)
    response = requests.post(url('sample', PROJECTID),
                             data=json.dumps(data),
                             headers=apikey)
    assert response.status_code == 201, response
    sample = response.json()
    assert sample['projectid'] == PROJECTID
    assert sample['sampleid'] == SAMPLEID
    data = dict(sampleid=SAMPLEID)
    response = requests.post(url('sample', PROJECTID),
                             data=json.dumps(data),
                             headers=apikey)
    assert response.status_code == 400, response
