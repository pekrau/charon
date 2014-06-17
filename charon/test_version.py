" Charon: nosetests /api/v1/version "

from charon.setup_test import *


def test_version():
    "Access version with header carrying API key."
    response = session.get(url('version'), headers=apikey)
    assert response.status_code == requests.codes.ok
    data = response.json()
    assert 'Charon' in data

def test_version_no_header():
    "No access without header carrying API key."
    response = session.get(url('version'))
    assert response.status_code == 401
