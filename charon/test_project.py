" Charon: nosetests /api/v1/project "

from charon.init_test import *

PROJECTID = 'P0'


def test_project_create_not_json():
    "Attempt to create a project with input data that is not JSON."
    response = session.post(url('project'),
                            data='% not JSON',
                            headers=api_token)
    assert response.status_code == 400, response

def test_project_create():
    "Create a project."
    data = dict(projectid=PROJECTID, name='P.Kraulis_13_01')
    response = session.post(url('project'),
                            data=json.dumps(data),
                            headers=api_token)
    assert response.status_code == 201, response
    project = response.json()
    assert project['projectid'] == PROJECTID, 'projectid must be same'

def test_no_such_project():
    "Access a non-existing project."
    response = session.get(url('project', 'no such project'), headers=api_token)
    assert response.status_code == 404, response

def test_projects_list():
    "Get the list of projects."
    response = session.get(url('projects'), headers=api_token)
    assert response.status_code == 200, response
    data = response.json()
    assert 'projects' in data, 'projects field in data'
    projects = data['projects']
    assert len(projects) >= 1, 'at least one project in list'
    project = None
    for p in projects:
        if p['projectid'] == PROJECTID:
            project = p
            break
    assert project, 'project must exist in list'

def test_project_modify():
    "Modify the fields of a project."
    response = session.get(url('project', PROJECTID), headers=api_token)
    assert response.status_code == 200, response
    olddata = response.json()
    data = dict(name=(olddata.get('name') or 'blah') + 'xyz_123')
    response = session.put(url('project', PROJECTID),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(url('project', PROJECTID), headers=api_token)
    assert response.status_code == 200, response
    newdata = response.json()
    assert newdata['_rev'] != olddata['_rev'], 'new document revision'
    assert newdata['name'] == data['name'], 'name must have been updated'
    assert newdata['name'] != olddata['name'], 'name must not be old value'

def test_project_modify_undef_field():
    "Try to modify undefined field."
    response = session.get(url('project', PROJECTID), headers=api_token)
    assert response.status_code == 200, response
    olddata = response.json()
    assert olddata.get('status') != 'brilliant'
    data = dict(stuff='garbage', status='brilliant')
    response = session.put(url('project', PROJECTID),
                           data=json.dumps(data),
                           headers=api_token)
    assert response.status_code == 204, response
    response = session.get(url('project', PROJECTID), headers=api_token)
    assert response.status_code == 200, response
    newdata = response.json()
    assert newdata['_rev'] != olddata['_rev'], 'new document revision'
    assert newdata.get('status') == 'brilliant', 'status must have been updated'
    assert newdata.get('stuff') is None, 'undef must not have been updated'

def test_project_delete():
    "Delete a project."
    response = session.delete(url('project', PROJECTID), headers=api_token)
    assert response.status_code == 204, response
    assert len(response.content) == 0, 'no content in response'
