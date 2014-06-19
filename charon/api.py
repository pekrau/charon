" Charon: base API request handlers. "

import json
import logging

import tornado.web
import couchdb
import requests

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .login import UserSaver


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


class ApiDocument(ApiRequestHandler):
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


class ApiNotify(ApiRequestHandler):
    """Notify this web service of an event in some other system.
    This web service is free to ignore the event.
    No API key is required for this call."""

    def check_api_access(self):
        pass

    def post(self):
        """Handle 'user' event; fetch new data.
        This assumes that Userman is the authentication server.
        """
        logging.debug('API notify')
        try:
            data = json.loads(self.request.body)
            logging.debug("API notify post data: %s", data)
            # Only the designated authentication server is allowed to do this.
            if not data.get('event') == 'user':
                raise ValueError("event is not 'user'")
            href = data.get('href', '')
            if not href.startswith(settings['AUTH']['HREF']):
                raise ValueError("wrong Userman host: %s", href)
        except Exception, msg:
            logging.warning("API notify post error: %s", msg)
            self.send_error(400, reason=str(msg))
        else:
            self.set_status(202)
            self.finish()
            try:
                headers = {'X-Userman-API-key': settings['AUTH']['API_KEY']}
                data = dict(service='Charon')
                response = requests.post(href, headers=headers,
                                         data=json.dumps(data))
                if response.status_code != requests.codes.ok:
                    raise ValueError("Userman error: %s %s",
                                     response.status_code,
                                     response.reason)
                data = response.json()
                user = self.get_user(data['email'])
                user.update(data)
                with UserSaver(doc=user, rqh=self):
                    pass            # Changes already made.
            except Exception, msg:
                logging.debug("API notify request error: %s", msg)
