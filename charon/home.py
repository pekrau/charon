" Charon: Home and other top pages in the interface. "

import logging
import json

import tornado.web
import couchdb

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .api import ApiRequestHandler


class Summary(RequestHandler):

    @tornado.web.authenticated
    def get(self):
        samples=self.get_samples()
        tot=0;
        ana=0
        passed=0
        failed=0
        runn=0
        for sample in samples:
            tot+=1
            if sample.get("analysis_status") == constants.SAMPLE_ANALYSIS_STATUS['DONE']:
                ana+=1
                passed+=1
            elif sample.get("analysis_status") == constants.SAMPLE_ANALYSIS_STATUS['FAILED']:
                ana+=1
                failed+=1
            elif sample.get("analysis_status") == constants.SAMPLE_ANALYSIS_STATUS['ONGOING']:
                runn+=1



        self.render('summary.html',samples_total=tot, samples_analyzed=ana,samples_passed=passed, samples_failed=failed, samples_running=runn)



class Home(RequestHandler):
    "Home page: Form to login or link to create new account. Links to pages."

    def get(self):
        try:
            samples_count = self.db.view('sample/count').rows[0].value
        except IndexError:
            samples_count = 0
        try:
            libpreps_count = self.db.view('libprep/count').rows[0].value
        except IndexError:
            libpreps_count = 0
        view = self.db.view('project/modified', limit=10,
                            descending=True,
                            include_docs=True)
        projects = [r.doc for r in view]
        view = self.db.view('sample/modified', limit=10,
                            descending=True,
                            include_docs=True)
        samples = [r.doc for r in view]
        view = self.db.view('libprep/modified', limit=10,
                            descending=True,
                            include_docs=True)
        libpreps = [r.doc for r in view]
        self.render('home.html',
                    projects_count=len(list(self.db.view('project/name'))),
                    samples_count=samples_count,
                    libpreps_count=libpreps_count,
                    projects=projects,
                    samples=samples,
                    libpreps=libpreps,
                    next=self.get_argument('next', ''))


class Search(RequestHandler):
    "Search page."

    @tornado.web.authenticated
    def get(self):
        term = self.get_argument('term', '')
        items = dict()
        if term:
            view = self.db.view('project/projectid')
            for row in view[term : term+constants.HIGH_CHAR]:
                doc = self.get_project(row.key)
                items[doc['_id']] = doc
            view = self.db.view('project/name')
            for row in view[term : term+constants.HIGH_CHAR]:
                doc = self.get_project(row.value)
                items[doc['_id']] = doc
            view = self.db.view('project/splitname')
            for row in view[term : term+constants.HIGH_CHAR]:
                doc = self.get_project(row.value)
                items[doc['_id']] = doc
            view = self.db.view('user/email')
            for row in view[term : term+constants.HIGH_CHAR]:
                doc = self.get_user(row.key)
                items[doc['_id']] = doc
            view = self.db.view('user/name')
            for row in view[term : term+constants.HIGH_CHAR]:
                doc = self.get_user(row.value)
                items[doc['_id']] = doc
        items = sorted(items.values(),
                       cmp=lambda i,j: cmp(i['modified'], j['modified']),
                       reverse=True)
        self.render('search.html',
                    term=term,
                    items=items)


class ApiHome(ApiRequestHandler):
    """API root: Links to API entry points.
    Every call to an API resource must include an API access
    token in the header.
    The key of the header record is 'X-Charon-API-token',
    and the value is a random hexadecimal string."""

    def get(self):
        """Return links to API entry points.
        Success: HTTP 200."""
        data = dict(links=dict(
                self=dict(href=self.get_absolute_url('api_home'),
                          title='API root'),
                version=dict(href=self.get_absolute_url('api_version'),
                             title='software versions'),
                projects=dict(href=self.get_absolute_url('api_projects'),
                              title='all projects'),
                ))
        self.write(data)


class Version(RequestHandler):
    "Page displaying the software component versions."

    def get(self):
        "Return version information for all software in the system."
        self.render('version.html', versions=utils.get_versions())


class ApiVersion(ApiRequestHandler):
    "Access to software component versions"

    def get(self):
        "Return software component versions."
        self.write(dict(utils.get_versions()))


class ApiDocumentation(RequestHandler):
    "Documentation of the API generated by introspection."

    def get(self):
        "Display only URLs beginning with '/api/'."
        hosts = []
        for handler in self.application.handlers:
            urlspecs = []
            hosts.append(dict(name=handler[0].pattern.rstrip('$'),
                              urlspecs=urlspecs))
            for urlspec in handler[1]:
                if not urlspec.regex.pattern.startswith('/api/'): continue
                saver = urlspec.handler_class.saver
                if saver is not None:
                    fields = saver.fields
                else:
                    fields = []
                methods = []
                for name in ('get', 'post', 'put', 'delete'):
                    method = getattr(urlspec.handler_class, name)
                    if method.__doc__ is None: continue
                    methods.append((name, self.process_text(method.__doc__)))
                urlspecs.append(dict(pattern=urlspec.regex.pattern.rstrip('$'),
                                     text=self.process_text(urlspec.handler_class.__doc__),
                                     fields=fields,
                                     methods=methods))
        self.render('apidoc.html', hosts=hosts)

    def process_text(self, text):
        if not text: return '-'
        lines = text.split('\n')
        if len(lines) >= 2:
            prefix = len(lines[1]) - len(lines[1].strip())
            for pos, line in enumerate(lines[1:]):
                try:
                    lines[pos+1] = line[prefix:]
                except IndexError:
                    pass
        return '\n'.join(lines)
