" Charon: nosetests /api/v1/version "

from charon.init_test import *


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
