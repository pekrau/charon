" Charon: nosetests /api/v1/libprep "

from charon.init_test import *

PROJECTID = 'P0'
SAMPLEID = 'S1'
LIBPREPID = 'A'
LIBPREPID2 = 'B'


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

@with_setup(my_setup, my_teardown)
def test_libprep_create():
    "Create a libprep."
    data = dict(libprepid=LIBPREPID)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    libprep = response.json()
    assert libprep['projectid'] == PROJECTID
    assert libprep['sampleid'] == SAMPLEID
    assert libprep['libprepid'] == LIBPREPID

@with_setup(my_setup, my_teardown)
def test_libprep_modify():
    "Create and modify a libprep."
    # Create the libprep, with status 'new'
    data = dict(libprepid=LIBPREPID, status='new')
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201
    libprep = response.json()
    assert libprep['projectid'] == PROJECTID
    assert libprep['sampleid'] == SAMPLEID
    assert libprep['libprepid'] == LIBPREPID
    assert libprep['status'] == 'new'
    # Modify the libprep, setting status to 'old'
    libprep_url = BASE_URL.rstrip('/') + response.headers['location']
    data = dict(status='old')
    response = session.put(libprep_url,
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(libprep_url, headers=api_token)
    assert response.status_code == 200, response
    libprep = response.json()
    assert libprep['status'] == 'old'

@with_setup(my_setup, my_teardown)
def test_libprep_create_collision():
    "Create a libprep, and try creating another with same name."
    data = dict(libprepid=LIBPREPID)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    libprep = response.json()
    assert libprep['projectid'] == PROJECTID
    assert libprep['sampleid'] == SAMPLEID
    assert libprep['libprepid'] == LIBPREPID
    data = dict(libprepid=LIBPREPID)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 400, response

@with_setup(my_setup, my_teardown)
def test_libprep_create_multiple():
    "Create several libpreps, obtain list of all."
    data = dict(libprepid=LIBPREPID)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    libprep = response.json()
    assert libprep['projectid'] == PROJECTID
    assert libprep['sampleid'] == SAMPLEID
    assert libprep['libprepid'] == LIBPREPID
    data = dict(libprepid=LIBPREPID2)
    response = session.post(url('libprep', PROJECTID, SAMPLEID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    libprep2 = response.json()
    assert libprep2['projectid'] == PROJECTID
    assert libprep2['sampleid'] == SAMPLEID
    assert libprep2['libprepid'] == LIBPREPID2
    assert libprep['_id'] != libprep2['_id']
    response = session.get(url('libpreps', PROJECTID, SAMPLEID),
                           headers=api_token)
    assert response.status_code == 200, response
    data = response.json()
    assert 'libpreps' in data
    assert len(data['libpreps']) == 2
