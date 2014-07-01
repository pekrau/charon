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
def test_libprep_seqruns():
    "Create some seqruns in a libprep, and manipulate those."
    response = session.get(url('libprep', PROJECTID, SAMPLEID, LIBPREPID),
                           headers=api_token)
    assert response.status_code == 200, response
    libprep = response.json()
    data = dict(status='initialized')
    response = session.post(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 204, response
    libprep_url = settings['BASE_URL'].rstrip('/') + response.headers['location']
    response = session.get(libprep_url, headers=api_token)
    assert response.status_code == 200, response
    data = response.json()
    seqruns = data['seqruns']
    assert len(seqruns) == 1
    response = session.get(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           headers=api_token)
    assert response.status_code == 200, response
    assert seqruns[0] == response.json()
    data = dict(status='done',
                alignment_status='started',
                flowcellid='123_xyz_qwerty')
    response = session.put(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           headers=api_token)
    newdata = response.json()
    assert data['flowcellid'] == newdata['flowcellid']
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
    data = dict(alignment_coverage=-0.1)
    response = session.put(url('seqrun', PROJECTID, SAMPLEID, LIBPREPID, 1),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 400, response
