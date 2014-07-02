" Charon: nosetests /api/v1/seqrun "

from charon.init_test import *

PROJECTID = 'P0'
SAMPLEID = 'S1'
LIBPREPID = 'A'


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


@with_setup(my_setup, my_teardown)
def test_create_seqrun():
    "Create a seqrun in a libprep and manipulate it."
    data = dict(status='initialized')
    response = session.post(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    data = response.json()
    assert data['projectid'] == PROJECTID
    assert data['sampleid'] == SAMPLEID
    assert data['libprepid'] == LIBPREPID
    assert data['seqrunid'] == 1, repr(data['seqrunid'])
    response = session.get(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           headers=api_token)
    assert response.status_code == 200, response
    assert data == response.json()
    data = dict(status='done',
                alignment_status='started',
                runid='123_xyz_qwerty')
    response = session.put(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           headers=api_token)
    newdata = response.json()
    assert data['runid'] == newdata['runid']
    data = dict(status='done',
                alignment_status='done',
                alignment_coverage=1.0)
    response = session.put(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           headers=api_token)
    newdata = response.json()
    assert data['alignment_coverage'] == newdata['alignment_coverage']
    data = dict(alignment_coverage=-1.0)
    response = session.put(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 400, response
