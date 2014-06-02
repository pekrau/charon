" Charon: Version interface. "

import logging

import tornado.web
import couchdb

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .api import ApiRequestHandler


class VersionMixin(object):

    def get_versions(self):
        return [('Charon', constants.VERSION),
                ('tornado', tornado.version),
                ('CouchDB server', settings['DB_SERVER_VERSION']),
                ('CouchDB module', couchdb.__version__)]


class Version(VersionMixin, RequestHandler):
    "Page displaying the software component versions."

    @tornado.web.authenticated
    def get(self):
        "Return version information for all software in the system."
        self.render('version.html', versions=self.get_versions())


class ApiVersion(VersionMixin, ApiRequestHandler):
    "Return software component versions."

    def get(self):
        self.write(dict(self.get_versions()))
