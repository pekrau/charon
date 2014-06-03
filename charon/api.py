" Charon: base API request handlers. "

import logging

import tornado.web
import couchdb

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler


class ApiRequestHandler(RequestHandler):
    "Check API key unless logged in."

    def prepare(self):
        super(ApiRequestHandler, self).prepare()
        self.check_api_access()

    def check_api_access(self):
        """Check the API key given in the header.
        Return HTTP 401 if invalid or missing key."""
        if self.get_current_user(): return
        try:
            apikey = self.request.headers['X-Charon-API-key']
        except KeyError:
            self.send_error(401, reason='API key missing')
        else:
            rows = list(self.db.view('user/apikey')[apikey])
            if len(rows) != 1:
                self.send_error(401, reason='invalid API key')
            else:
                try:
                    user = self.get_user(rows[0].value)
                except KeyError:
                    self.send_error(401, reason='invalid user email')
                else:
                    if user.get('status') == constants.ACTIVE:
                        self._user = user
                        logging.debug("API key accept user '%s'", user['email'])
                    else:
                        self.send_error(401, reason='user not active')


class ApiDoc(ApiRequestHandler):
    "Access a database document as is."

    def get(self, id):
        "Return a database document as is."
        try:
            self.write(self.db[id])
        except couchdb.http.ResourceNotFound:
            self.send_error(404, reason='no such item')


class ApiLogs(ApiRequestHandler):
    "Access log event documents for a given document."

    def get(self, id):
        "Return all log event documents for a given document."
        self.write(dict(logs=self.get_logs(id)))
