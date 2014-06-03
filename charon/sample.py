" Charon: Sample interface. "

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


class SampleSaver(DocumentSaver):
    doctype = constants.SAMPLE
    field_keys = ['sampleid',
                  'status',
                  'received',
                  'qc',
                  'genotyping_status',
                  'genotyping_concordance',
                  'requires_more_sequence',
                  'sequenced',
                  'primary_analysis_done',
                  'secondary_analysis_done',
                  'delivered',
                  ]

    def __init__(self, doc=None, rqh=None, db=None, project=None):
        super(SampleSaver, self).__init__(doc=doc, rqh=rqh, db=db)
        if self.is_new():
            assert project, 'project must be defined'
            assert 'projectid' not in self.doc, 'projectid must not be set'
            self.doc['projectid'] = project['projectid']
            self.project = project
        else:
            if project:
                assert self.doc['projectid'] == project['projectid'], \
                    'project must be same as at creation, if given'
                self.project = project
            else:
                self.project = rqh.get_project(self.doc['projectid'])

    def check_sampleid(self, value):
        if self.is_new():
            if not value:
                raise ValueError('sampleid must have a defined value')
            key = (self.project['projectid'], value)
            rows = list(self.db.view('sample/sampleid')[key])
            if len(rows) > 0:
                raise ValueError('sampleid is not unique')

    def convert_sampleid(self, value):
        "No change allowed after creation."
        if self.is_new():
            return value
        else:
            return self.doc['sampleid']

    def convert_status(self, value): return value or None
    def convert_qc(self, value): return value or None
    def convert_genotyping_status(self, value): return value or None
    def convert_genotyping_concordance(self, value): return value or None


class Sample(RequestHandler):
    "Display the sample data."

    @tornado.web.authenticated
    def get(self, projectid, sampleid):
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libpreps = self.get_libpreps(projectid, sampleid)
        self.render('sample.html',
                    project=project,
                    sample=sample,
                    libpreps=libpreps,
                    logs=self.get_logs(sample['_id']))


class ApiSample(ApiRequestHandler):
    "Return the sample data, or edit the sample."

    def get(self, projectid, sampleid):
        "Return the sample data as JSON."
        sample = self.get_sample(projectid, sampleid)
        if not sample: return
        self.write(sample)

    def put(self, projectid, sampleid):
        """Update the sample fields with the given JSON data.
        Return HTTP 204 "No Content".
        Return HTTP 400 if there is some problem with the input data.
        Return HTTP 409 if there is a document revision conflict."""
        sample = self.get_sample(projectid, sampleid)
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with SampleSaver(doc=sample, rqh=self) as saver:
                    saver.update(data=data)
            except ValueError, msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                self.set_status(204)


class SampleCreate(RequestHandler):
    "Create a sample."

    @tornado.web.authenticated
    def get(self, projectid):
        self.render('sample_create.html', project=self.get_project(projectid))

    @tornado.web.authenticated
    def post(self, projectid):
        self.check_xsrf_cookie()
        project = self.get_project(projectid)
        try:
            with SampleSaver(rqh=self, project=project) as saver:
                saver.update()
                sample = saver.doc
        except ValueError, msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except IOError, msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        else:
            url = self.reverse_url('sample', projectid, sample['sampleid'])
            self.redirect(url)


class ApiSampleCreate(ApiRequestHandler):
    "Create a sample within a project."

    def post(self, projectid):
        """Create a sample within a project.
        JSON data:
          XXX
        Return HTTP 201, the sample URL as Location, and the sample data.
        Return HTTP 400 if something is wrong with the values.
        Return HTTP 409 if there is a document revision conflict."""
        project = self.get_project(projectid)
        if not project: return
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with SampleSaver(rqh=self, project=project) as saver:
                    saver.update(data=data)
                    sample = saver.doc
            except (KeyError, ValueError), msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                logging.debug("created sample %s", sample['sampleid'])
                url = self.reverse_url('api_sample',
                                       projectid,
                                       sample['sampleid'])
                self.set_header('Location', url)
                self.set_status(201)
                self.write(sample)


class SampleEdit(RequestHandler):
    "Edit an existing sample."

    @tornado.web.authenticated
    def get(self, projectid, sampleid):
        sample = self.get_sample(projectid, sampleid)
        self.render('sample_edit.html', sample=sample)

    @tornado.web.authenticated
    def post(self, projectid, sampleid):
        self.check_xsrf_cookie()
        sample = self.get_sample(projectid, sampleid)
        try:
            with SampleSaver(doc=sample, rqh=self) as saver:
                saver.update()
        except ValueError, msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except IOError, msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        else:
            url = self.reverse_url('sample', projectid, sampleid)
            self.redirect(url)


class ApiSamples(ApiRequestHandler):
    "Access to all samples in a project."

    def get(self, projectid):
        "Return a list of all samples."
        samples = self.get_samples(projectid)
        self.write(dict(samples=samples))
