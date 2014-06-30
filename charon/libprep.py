" Charon: Libprep entity interface. "

import logging
import json

import tornado.web
import couchdb

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .api import ApiRequestHandler
from .saver import *


class LibprepidField(IdField):
    "The unique identifier for the libprep within the sample."

    def check_unique(self, saver, value):
        key = (saver.project['projectid'], saver.sample['sampleid'], value)
        view = saver.db.view('libprep/libprepid')
        if len(list(view[key])) > 0:
            raise ValueError('libprepid is not unique')
        return value


class LibprepSaver(Saver):
    "Saver and fields definions for the libprep entity."

    doctype = constants.LIBPREP

    fields = [LibprepidField('libprepid', title='Identifier'),
              Field('status',description='The status of the libprep.'),
              ]

    def __init__(self, doc=None, rqh=None, db=None, sample=None):
        super(LibprepSaver, self).__init__(doc=doc, rqh=rqh, db=db)
        if self.is_new():
            assert sample
            assert 'sampleid' not in self.doc
            self.sample = sample
            self.project = rqh.get_project(sample['projectid'])
            self.doc['projectid'] = sample['projectid']
            self.doc['sampleid'] = sample['sampleid']
            self.doc['seqruns'] = []
        else:
            self.project = rqh.get_project(self.doc['projectid'])
            if sample:
                assert (self.doc['sampleid'] == sample['sampleid']) and \
                    (self.doc['projectid'] == sample['projectid'])
                self.sample = sample
            else:
                self.sample = rqh.get_sample(self.doc['projectid'],
                                             self.doc['sampleid'])

    def update_seqrun(self, pos, seqrun=None):
        "Create or update a given seqrun within the libprep."
        if seqrun is None:
            seqrun = dict(status=self.rqh.get_argument('status', None),
                          flowcellid=self.rqh.get_argument('flowcellid', None),
                          alignment_status=self.rqh.get_argument('alignment_status', None),
                          alignment_coverage=self.rqh.get_argument('alignment_coverage', None))
        coverage = seqrun.get('alignment_coverage', None)
        if coverage is not None:
            try:
                coverage = float(coverage)
                if coverage < 0.0: raise ValueError
            except (ValueError, TypeError):
                raise tornado.web.HTTPError(400, 'invalid alignment_coverage value')
            seqrun['alignment_coverage'] = coverage
        if pos is None:
            seqruns = self.doc['seqruns'] + [seqrun]
        else:
            seqruns = list(self.doc['seqruns']) # List copy required here!
            seqruns[pos] = seqrun
        # Don't go via setitem, since that is blocked by checker.
        self.doc['seqruns'] = seqruns
        self.changed['seqruns'] = seqruns


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


class LibprepCreate(RequestHandler):
    "Create a libprep."

    saver = LibprepSaver

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
            with self.saver(rqh=self, sample=sample) as saver:
                saver.store()
                libprep = saver.doc
        except (IOError, ValueError), msg:
            self.render('libprep_create.html',
                        project=self.get_project(projectid),
                        sample=self.get_sample(projectid, sampleid),
                        fields=self.libprep.fields,
                        error=str(error))
        else:
            url = self.reverse_url('libprep',
                                   projectid,
                                   sampleid,
                                   libprep['libprepid'])
            self.redirect(url)


class LibprepEdit(RequestHandler):
    "Edit an existing libprep."

    saver = LibprepSaver

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid):
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        self.render('libprep_edit.html', libprep=libprep)

    @tornado.web.authenticated
    def post(self, projectid, sampleid, libprepid):
        self.check_xsrf_cookie()
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            with self.saver(doc=libprep, rqh=self) as saver:
                saver.store()
        except ValueError, msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except IOError, msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        else:
            url = self.reverse_url('libprep', projectid, sampleid, libprepid)
            self.redirect(url)


class ApiLibprep(ApiRequestHandler):
    "Access a libprep."

    saver = LibprepSaver

    def get(self, projectid, sampleid, libprepid):
        """Return the libprep data as JSON.
        Return HTTP 404 if no such libprep, sample or project."""
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        if not libprep: return
        self.add_link(libprep, 'project', 'api_project', projectid)
        self.add_link(libprep, 'sample', 'api_sample', projectid, sampleid)
        self.add_link(libprep, 'self', 'api_libprep', projectid, sampleid, libprepid)
        self.add_link(libprep, 'logs', 'api_logs', libprep['_id'])
        self.write(libprep)

    def put(self, projectid, sampleid, libprepid):
        """Update the libprep with the given JSON data.
        Return HTTP 204 "No Content".
        Return HTTP 400 if the input data is invalid.
        Return HTTP 409 if there is a document revision conflict."""
        try:
            libprep = self.get_libprep(projectid, sampleid, libprepid)
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with self.saver(doc=libprep, rqh=self) as saver:
                    saver.store(data=data)
            except ValueError, msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                self.set_status(204)


class ApiLibprepCreate(ApiRequestHandler):
    "Create a libprep within a sample."

    saver = LibprepSaver

    def post(self, projectid, sampleid):
        """Create a libprep within a sample.
        JSON data:
          XXX
        Return HTTP 201, libprep URL in header "Location", and libprep data.
        Return HTTP 400 if something is wrong with the input data.
        Return HTTP 404 if no such project or sample.
        Return HTTP 409 if there is a document revision conflict."""
        project = self.get_project(projectid)
        if not project: return
        sample = self.get_sample(projectid, sampleid)
        if not sample: return
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with self.saver(rqh=self, sample=sample) as saver:
                    saver.store(data=data)
                    libprep = saver.doc
            except (KeyError, ValueError), msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                logging.debug("created libprep %s", libprep['libprepid'])
                url = self.reverse_url('api_libprep',
                                       projectid,
                                       sampleid,
                                       libprep['libprepid'])
                self.set_header('Location', url)
                self.set_status(201)
                self.write(libprep)


class ApiProjectLibpreps(ApiRequestHandler):
    "Access to all libpreps for a project."

    def get(self, projectid):
        "Return a list of all libpreps for the given project."
        libpreps = self.get_libpreps(projectid)
        for libprep in libpreps:
            self.add_link(libprep, 'project', 'api_project', projectid)
            self.add_link(libprep, 'sample', 'api_sample', projectid,
                          libprep['sampleid'])
            self.add_link(libprep, 'self', 'api_libprep', projectid,
                          libprep['sampleid'], libprep['libprepid'])
            self.add_link(libprep, 'logs', 'api_logs', libprep['_id'])
        self.write(dict(libpreps=libpreps))


class ApiSampleLibpreps(ApiRequestHandler):
    "Access to all libpreps for a sample."

    def get(self, projectid, sampleid):
        "Return a list of all libpreps for the given sample and project."
        libpreps = self.get_libpreps(projectid, sampleid)
        for libprep in libpreps:
            self.add_link(libprep, 'project', 'api_project', projectid)
            self.add_link(libprep, 'sample', 'api_sample', projectid,
                          libprep['sampleid'])
            self.add_link(libprep, 'self', 'api_libprep', projectid,
                          libprep['sampleid'], libprep['libprepid'])
            self.add_link(libprep, 'logs', 'api_logs', libprep['_id'])
        self.write(dict(libpreps=libpreps))
