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
              SelectField('analysis_status',
                          description='The status of the sample\'s analysis .',
                          options=constants.ANALYSIS_STATUS),
              SelectField('qc_status', title='QC',
                    description='The quality control status of the sample\'s analysis.', options=constants.EXTENDED_STATUS),
              SelectField('genotyping_status',
                    description='The genotyping status of the sample.', options=constants.GENO_STATUS),
              FloatField('total_autosomal_coverage',
                    description='Total of every autosomal coverage for each seqrun in each libprep.', 
                    default=0.0),
              FloatField('total_sequenced_reads',
                    description='Total of all for each seqrun in each libprep.'),
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

    # Do not use authenticaton decorator; do not send to login page, but fail.
    def get(self, projectid, sampleid):
        """Return the sample data as JSON.
        Return HTTP 404 if no such sample or project."""
        sample = self.get_sample(projectid, sampleid)
        if not sample: return
        self.add_sample_links(sample)
        self.write(sample)

    # Do not use authenticaton decorator; do not send to login page, but fail.
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
    
    # Do not use authenticaton decorator; do not send to login page, but fail.
    def delete(self, projectid, sampleid):
        """NOTE: This is for unit test purposes only!
        Delete the sample and all of its dependent entities.
        Returns HTTP 204 "No Content"."""
        sample= self.get_sample(projectid, sampleid)
        if not sample: return
        utils.delete_sample(self.db, sample)
        logging.debug("deleted sample {0}, {1}".format(projectid, sampleid))
        self.set_status(204)


class ApiSampleCreate(ApiRequestHandler):
    "Create a sample within a project."

    saver = SampleSaver

    # Do not use authenticaton decorator; do not send to login page, but fail.
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

    # Do not use authenticaton decorator; do not send to login page, but fail.
    def get(self, projectid):
        "Return a list of all samples."
        samples = self.get_samples(projectid)
        for sample in samples:
            self.add_sample_links(sample)
        self.write(dict(samples=samples))


class ApiSamplesNotDone(ApiRequestHandler):
    "Access to all samples that are not done."

    # Do not use authenticaton decorator; do not send to login page, but fail.
    def get(self):
        "Return a list of all undone samples."
        samples= self.get_not_done_samples()
        for sample in samples:
            self.add_sample_links(sample)
        self.write(dict(samples=samples))


class ApiSamplesNotDonePerProject(ApiRequestHandler):
    "Access to all samples that are not done."

    # Do not use authenticaton decorator; do not send to login page, but fail.
    def get(self, projectid):
        "Return a list of all undone samples."
        samples= self.get_not_done_samples(projectid)
        for sample in samples:
            self.add_sample_links(sample)
        self.write(dict(samples=samples))


class ApiSamplesCustomQuery(ApiRequestHandler):
    """Access to all samples that match the given query. The query MUST be a dictionnary with
    the following keys : projectid, sampleField, operator, value, type.
    ex : {'projectid':'P567', 'sampleField':'total_sequenced_reads', 'operator':'>=' , 'value':10, 'type':'float'}"""

    # Do not use authenticaton decorator; do not send to login page, but fail.
    def get(self):
        "Return a list of all samples matching the query."
        try:
            data = json.loads(self.request.body)
            if 'projectid' not in data:
                raise KeyError('data given does not contain a projectid')
            if 'sampleField' not in data:
                raise KeyError('data given does not contain a sampleField')
            if 'operator' not in data:
                raise KeyError('data given does not contain an operator ')
            if 'type' not in data:
                raise KeyError('data given does not contain a type')
            if 'value' not in data:
                raise KeyError('data given does not contain a value')
            if  data['operator'] not in ['==', '>', '<', '<=', '>=', 'is']:
                raise ValueError('Unallowed operator : {0}'.format(data['operator']))
            allsamples= self.get_samples(data['projectid'])
            samples=[]
            query="sample.get('"+data['sampleField']+"') "+data['operator']+" "+data['type']+"("+data['value']+")"
        except Exception, msg:
            self.send_error(400, reason=str(msg))

        for sample in allsamples:
            try:
                if not sample.get(data['sampleField']):
                    #if the field is not in the db, just skip the doc
                    continue
                if type(sample.get(data['sampleField'])).__name__ != data['type']:
                    raise TypeError('Given type does not match database type {0}'.format(type(sample.get(data['sampleField'])).__name__))
                if eval(query, {"__builtins__":None}, {'sample':sample, 'int':int, 'str':str, 'float':float} ):
                    samples.append(sample)
            except Exception, msg:
                self.send_error(400, reason=str(msg))
        for sample in samples:
            self.add_sample_links(sample)
        self.write(dict(samples=samples))
