" Charon: Libprep interface. "

import logging
import json

import tornado.web
import couchdb

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .api import ApiRequestHandler
from .saver import DocumentSaver


class LibprepSaver(DocumentSaver):
    doctype = constants.LIBPREP
    # 'seqruns' not here, since must be updated only via /seqrun interface
    field_keys = ['libprepid', 'status']

    def __init__(self, doc=None, rqh=None, db=None, sample=None):
        super(LibprepSaver, self).__init__(doc=doc, rqh=rqh, db=db)
        if self.is_new():
            assert sample, 'sample must be defined'
            assert 'sampleid' not in self.doc, 'sampleid must not be set'
            self.sample = sample
            self.project = rqh.get_project(sample['projectid'])
            self.doc['projectid'] = sample['projectid']
            self.doc['sampleid'] = sample['sampleid']
            self.doc['seqruns'] = []
        else:
            if sample:
                assert (self.doc['sampleid'] == sample['sampleid']) and \
                    (self.doc['projectid'] == sample['projectid']), \
                    'sample must be same as at creation, if given'
                self.sample = sample
            else:
                self.sample = rqh.get_sample(self.doc['projectid'],
                                             self.doc['sampleid'])
            self.project = rqh.get_project(self.doc['projectid'])

    def check_libprepid(self, value):
        if self.is_new():
            if not value:
                raise ValueError('libprepid must have a defined value')
            key = (self.project['projectid'], self.sample['sampleid'], value)
            rows = list(self.db.view('libprep/libprepid')[key])
            if len(rows) > 0:
                raise ValueError('libprepid is not unique')

    def convert_libprepid(self, value):
        "No change allowed after creation."
        if self.is_new():
            return value
        else:
            return self.doc['libprepid']

    def convert_status(self, value): return value or None


class Libprep(RequestHandler):
    "Display the libprep data."

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid):
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        self.render('libprep.html',
                    project=project,
                    sample=sample,
                    libprep=libprep,
                    logs=self.get_logs(libprep['_id']))


class ApiLibprep(ApiRequestHandler):
    "Return the libprep data, or edit the libprep."

    def get(self, projectid, sampleid, libprepid):
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        if not libprep: return
        self.write(libprep)

    def put(self, projectid, sampleid, libprepid):
        """Update the libprep fields with the given data.
        Return HTTP 204 "No Content"."""
        try:
            libprep = self.get_libprep(projectid, sampleid, libprepid)
            data = json.loads(self.request.body)
        except Exception, msg:
            self.http_error(400, msg)
        else:
            try:
                with LibprepSaver(doc=libprep, rqh=self) as saver:
                    saver.update(data=data)
            except ValueError, msg:
                self.http_error(400, msg)
            except IOError, msg:
                self.http_error(409, msg)
            else:
                self.set_status(204)


class LibprepCreate(RequestHandler):
    "Create a libprep."

    @tornado.web.authenticated
    def get(self, projectid, sampleid):
        self.render('libprep_create.html',
                    project=self.get_project(projectid),
                    sample=self.get_sample(projectid, sampleid))

    @tornado.web.authenticated
    def post(self, projectid, sampleid):
        self.check_xsrf_cookie()
        sample = self.get_sample(projectid, sampleid)
        try:
            with LibprepSaver(rqh=self, sample=sample) as saver:
                saver.update()
                libprep = saver.doc
        except ValueError, msg:
            self.http_error(400, msg)
        except IOError, msg:
            self.http_error(409, msg)
        else:
            url = self.reverse_url('libprep',
                                   projectid,
                                   sampleid,
                                   libprep['libprepid'])
            self.redirect(url)


class ApiLibprepCreate(ApiRequestHandler):
    "Create a libprep given its data and return the URL as Location in header."

    def post(self, projectid, sampleid):
        project = self.get_project(projectid)
        if not project: return
        sample = self.get_sample(projectid, sampleid)
        if not sample: return
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.http_error(400, msg)
        else:
            try:
                with LibprepSaver(rqh=self, sample=sample) as saver:
                    saver.update(data=data)
                    libprep = saver.doc
            except (KeyError, ValueError), msg:
                self.http_error(400, msg)
            except IOError, msg:
                self.http_error(409, msg)
            else:
                logging.debug("created libprep %s", libprep['libprepid'])
                url = self.reverse_url('api_libprep',
                                       projectid,
                                       sampleid,
                                       libprep['libprepid'])
                self.set_header('Location', url)
                self.set_status(201)
                self.write(libprep)


class LibprepEdit(RequestHandler):
    "Edit an existing libprep."

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid):
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        self.render('libprep_edit.html', libprep=libprep)

    @tornado.web.authenticated
    def post(self, projectid, sampleid, libprepid):
        self.check_xsrf_cookie()
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            with LibprepSaver(doc=libprep, rqh=self) as saver:
                saver.update()
        except ValueError, msg:
            self.http_error(400, msg)
        except IOError, msg:
            self.http_error(409, msg)
        else:
            url = self.reverse_url('libprep', projectid, sampleid, libprepid)
            self.redirect(url)


class ApiLibpreps(ApiRequestHandler):
    "Return a list of all libpreps for the given sample."

    def get(self, projectid, sampleid):
        libpreps = self.get_libpreps(projectid, sampleid)
        self.write(dict(libpreps=libpreps))
