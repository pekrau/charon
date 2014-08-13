" Charon: Sample entity interface. "

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


class SampleidField(IdField):
    "The unique identifier for the sample within the project."

    def check_valid(self, saver, value):
        "Also check uniqueness."
        super(SampleidField, self).check_valid(saver, value)
        key = (saver.project['projectid'], value)
        view = saver.db.view('sample/sampleid')
        if len(list(view[key])) > 0:
            raise ValueError('not unique')


class SampleSaver(Saver):
    "Saver and fields definitions for the sample entity."

    doctype = constants.SAMPLE

    fields = [SampleidField('sampleid', title='Identifier'),
              SelectField('status',
                          description='The status of the sample.',
                          options=EXTENDED_STATUS),
              Field('received',
                    description='The reception date of the sample.'),
              SelectField('qc_status', title='QC',
                    description='The quality control status of the sample.', options=EXTENDED_STATUS),
              SelectField('genotyping_status',
                    description='The genotyping status of the sample.', options=GENO_STATUS),
              Field('genotyping_concordance',
                    description='The genotyping concordance of the sample.'),
              Field('lims_initial_qc',
                    description='Quality status of the received sample.'),
              FloatField('total_autosomal_coverage',
                    description='Total of every autosomal coverage for each seqrun in each libprep.'),
              ]

    def __init__(self, doc=None, rqh=None, db=None, project=None):
        super(SampleSaver, self).__init__(doc=doc, rqh=rqh, db=db)
        if self.is_new():
            assert project
            assert 'projectid' not in self.doc
            self.doc['projectid'] = project['projectid']
            self.project = project
        else:
            if project:
                assert self.doc['projectid'] == project['projectid']
                self.project = project
            else:
                self.project = rqh.get_project(self.doc['projectid'])


class Sample(RequestHandler):
    "Display the sample data."

    saver = SampleSaver

    @tornado.web.authenticated
    def get(self, projectid, sampleid):
        sample = self.get_sample(projectid, sampleid)
        libpreps = self.get_libpreps(projectid, sampleid)
        view = self.db.view('seqrun/count')
        for libprep in libpreps:
            try:
                startkey = [projectid, sampleid, libprep['libprepid']]
                endkey = [projectid, sampleid, libprep['libprepid'],
                          constants.HIGH_CHAR]
                row = view[startkey:endkey].rows[0]
            except IndexError:
                libprep['seqruns_count'] = 0
            else:
                libprep['seqruns_count'] = row.value
        logs = self.get_logs(sample['_id']) # XXX limit?
        self.render('sample.html',
                    sample=sample,
                    libpreps=libpreps,
                    fields=self.saver.fields,
                    logs=logs)


class SampleCreate(RequestHandler):
    "Create a sample."

    saver = SampleSaver

    @tornado.web.authenticated
    def get(self, projectid):
        self.render('sample_create.html',
                    project=self.get_project(projectid),
                    fields=self.saver.fields)

    @tornado.web.authenticated
    def post(self, projectid):
        self.check_xsrf_cookie()
        project = self.get_project(projectid)
        try:
            with self.saver(rqh=self, project=project) as saver:
                saver.store()
                sample = saver.doc
        except (IOError, ValueError), msg:
            self.render('sample_create.html',
                        project=project,
                        fields=self.saver.fields,
                        error=str(msg))
        else:
            url = self.reverse_url('sample', projectid, sample['sampleid'])
            self.redirect(url)


class SampleEdit(RequestHandler):
    "Edit an existing sample."

    saver = SampleSaver

    @tornado.web.authenticated
    def get(self, projectid, sampleid):
        sample = self.get_sample(projectid, sampleid)
        self.render('sample_edit.html',
                    sample=sample,
                    fields=self.saver.fields)

    @tornado.web.authenticated
    def post(self, projectid, sampleid):
        self.check_xsrf_cookie()
        sample = self.get_sample(projectid, sampleid)
        try:
            with self.saver(doc=sample, rqh=self) as saver:
                saver.store()
        except (IOError, ValueError), msg:
            self.render('sample_edit.html',
                        sample=sample,
                        fields=self.saver.fields,
                        error=str(msg))
        else:
            url = self.reverse_url('sample', projectid, sampleid)
            self.redirect(url)


class ApiSample(ApiRequestHandler):
    "Access a sample."

    saver = SampleSaver

    def get(self, projectid, sampleid):
        """Return the sample data as JSON.
        Return HTTP 404 if no such sample or project."""
        sample = self.get_sample(projectid, sampleid)
        if not sample: return
        self.add_sample_links(sample)
        self.write(sample)

    def put(self, projectid, sampleid):
        """Update the sample with the given JSON data.
        Return HTTP 204 "No Content".
        Return HTTP 400 if the input data is invalid.
        Return HTTP 409 if there is a document revision conflict."""
        sample = self.get_sample(projectid, sampleid)
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with self.saver(doc=sample, rqh=self) as saver:
                    saver.store(data=data)
            except ValueError, msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                self.set_status(204)


class ApiSampleCreate(ApiRequestHandler):
    "Create a sample within a project."

    saver = SampleSaver

    def post(self, projectid):
        """Create a sample within a project.
        Return HTTP 201, sample URL in header "Location", and sample data.
        Return HTTP 400 if something is wrong with the input data.
        Return HTTP 404 if no such project.
        Return HTTP 409 if there is a document revision conflict."""
        project = self.get_project(projectid)
        if not project: return
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with self.saver(rqh=self, project=project) as saver:
                    saver.store(data=data)
                    sample = saver.doc
            except (KeyError, ValueError), msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                url = self.reverse_url('api_sample',
                                       projectid,
                                       sample['sampleid'])
                self.set_header('Location', url)
                self.set_status(201)
                self.add_sample_links(sample)
                self.write(sample)


class ApiSamples(ApiRequestHandler):
    "Access to all samples in a project."

    def get(self, projectid):
        "Return a list of all samples."
        samples = self.get_samples(projectid)
        for sample in samples:
            self.add_sample_links(sample)
        self.write(dict(samples=samples))
