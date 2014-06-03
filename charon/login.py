" Charon: Login interface. "

import logging
import json

import tornado.web
import couchdb
import requests

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .saver import DocumentSaver


class UserSaver(DocumentSaver):
    doctype = constants.USER


class Login(RequestHandler):
    "Login handler."

    def get(self):
        self.render('login.html',
                    error=None,
                    next=self.get_argument('next', None))

    def post(self):
        self.check_xsrf_cookie()
        email = self.get_argument('email', '')
        password = self.get_argument('password', '')
        if email and password:
            data = dict(user=email,
                        password=password,
                        service='Charon')
            headers = {'X-Userman-API-key': settings['USERMAN_API_KEY']}
            response = requests.post(settings['USERMAN_URL'],
                                     data=json.dumps(data),
                                     headers=headers)
            if response.status_code == requests.codes.ok:
                try:
                    user = self.get_user(email)
                except tornado.web.HTTPError:
                    user = response.json()
                else:
                    user.update(response.json())
                with UserSaver(doc=user, rqh=self) as saver:
                    pass        # Changes already made.
                self.set_secure_cookie(constants.USER_COOKIE_NAME, email)
                url = self.get_argument('next', None)
                if not url:
                    url = self.reverse_url('home')
                self.redirect(url)
                return
        self.render('login.html',
                    error='invalid user or password',
                    next=self.get_argument('next', None))


class Logout(RequestHandler):
    "Logout handler."

    def post(self):
        self.check_xsrf_cookie()
        self.set_secure_cookie(constants.USER_COOKIE_NAME, '')
        self.redirect(self.reverse_url('login'))
