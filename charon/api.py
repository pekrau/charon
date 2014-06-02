" Charon: API handlers. "

import logging

import tornado.web
import couchdb

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler


class ApiRequestHandler(RequestHandler):
    """Check API key if not logged in.
    Redefine error method to output JSON body."""

    def prepare(self):
        super(ApiRequestHandler, self).prepare()
        self.check_api_access()

    def error(self, status_code, reason):
        self.send_error(status_code, reason=reason)

    def check_api_access(self):
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
                        logging.debug("API key accepted for user '%s'",
                                      user['email'])
                    else:
                        self.send_error(401, reason='user not active')

    def write_error(self, status_code, **kwargs):
        self.set_header('Content-Type', 'application/json')
        self.write(kwargs)


class ApiDoc(ApiRequestHandler):
    "Return a database document as is."

    def get(self, id):
        try:
            self.write(self.db[id])
        except couchdb.http.ResourceNotFound:
            self.send_error(404)


class ApiLogs(ApiRequestHandler):
    "Return all log event documents for a given document."

    def get(self, id):
        self.write(dict(logs=self.get_logs(id)))
