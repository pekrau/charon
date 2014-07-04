" Charon: Seqrun entity (part of libprep) interface. "

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


class SeqrunidField(Field):
    "The unique integer identifier for the seqrun within the libprep."

    def __init__(self, key):
        super(SeqrunidField, self).__init__(key,
                                            mandatory=True,
                                            editable=False)

    def get(self, saver, data=None):
        "Compute the value from the number of existing seqruns."
        key = [saver['projectid'], saver['sampleid'], saver['libprepid']]
        view = saver.db.view('seqrun/count')
        try:
            row = view[key].rows[0]
        except IndexError:
            return 1
        else:
            return row.value + 1

    def html_create(self, entity=None):
        "Return the field HTML input field for a create form."
        return '[autoassigned]'

    def html_edit(self, entity):
        "Return the field HTML input field for an edit form."
        return entity.get(self.key) or '-'


class SeqrunSaver(Saver):
    "Saver and fields definitions for the seqrun entity."

    doctype = constants.SEQRUN

    fields = [SeqrunidField('seqrunid'),
              Field('status', description='The status of the seqrun.'),
              Field('runid',
                    description='The flowcell+lane identifier.'),
              Field('alignment_status',
                    description='Status of the alignment of data to the reference genome.'),
              RangeFloatField('alignment_coverage', 
                              minimum=0.0,
                              description='The coverage of the reference'
                              ' genome, in percent.'),
              ]

    def __init__(self, doc=None, rqh=None, db=None, libprep=None):
        super(SeqrunSaver, self).__init__(doc=doc, rqh=rqh, db=db)
        if self.is_new():
            assert libprep
            assert 'libprepid' not in self.doc
            self.project = rqh.get_project(libprep['projectid'])
            self.sample = rqh.get_sample(libprep['projectid'],
                                         libprep['sampleid'])
            self.libprep = libprep
            self.doc['projectid'] = libprep['projectid']
            self.doc['sampleid'] = libprep['sampleid']
            self.doc['libprepid'] = libprep['libprepid']
        else:
            self.project = rqh.get_project(self.doc['projectid'])
            self.sample = rqh.get_sample(self.doc['projectid'],
                                         self.doc['sampleid'])
            if libprep:
                assert (self.doc['libprepid'] == libprep['libprepid']) and \
                    (self.doc['projectid'] == libprep['projectid'])
                self.libprep = libprep
            else:
                self.libprep = rqh.get_libprep(self.doc['projectid'],
                                               self.doc['sampleid'],
                                               self.doc['libprepid'])


class Seqrun(RequestHandler):
    "Display the seqrun data."

    saver = SeqrunSaver

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid, seqrunid):
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        seqrun = self.get_seqrun(projectid, sampleid, libprepid, seqrunid)
        logs = self.get_logs(seqrun['_id']) # XXX limit?
        self.render('seqrun.html',
                    project=project,
                    sample=sample,
                    libprep=libprep,
                    seqrun=seqrun,
                    fields=self.saver.fields,
                    logs=logs)


class SeqrunCreate(RequestHandler):
    "Create a seqrun within a libprep."

    saver = SeqrunSaver

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid):
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        self.render('seqrun_create.html',
                    libprep=libprep,
                    fields=self.saver.fields)

    @tornado.web.authenticated
    def post(self, projectid, sampleid, libprepid):
        self.check_xsrf_cookie()
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            with self.saver(rqh=self, libprep=libprep) as saver:
                saver.store()
                seqrun = saver.doc
        except (IOError, ValueError), msg:
            self.render('seqrun_create.html',
                        libprep=libprep,
                        fields=self.saver.fields,
                        error=str(msg))
        else:
            url = self.reverse_url('seqrun',
                                   projectid,
                                   sampleid,
                                   libprepid,
                                   seqrun['seqrunid'])
            self.redirect(url)


class SeqrunEdit(RequestHandler):
    "Edit an existing seqrun."

    saver = SeqrunSaver

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid, seqrunid):
        seqrun = self.get_seqrun(projectid, sampleid, libprepid, seqrunid)
        self.render('seqrun_edit.html',
                    seqrun=seqrun,
                    fields=self.saver.fields)

    @tornado.web.authenticated
    def post(self, projectid, sampleid, libprepid, seqrunid):
        self.check_xsrf_cookie()
        seqrun = self.get_seqrun(projectid, sampleid, libprepid, seqrunid)
        try:
            with self.saver(doc=seqrun, rqh=self) as saver:
                saver.store()
        except (IOError, ValueError), msg:
            self.render('seqrun_edit.html',
                        seqrun=seqrun,
                        fields=self.saver.fields,
                        error=str(msg))
        else:
            url = self.reverse_url('seqrun', projectid, sampleid, libprepid, seqrunid)
            self.redirect(url)


class ApiSeqrun(ApiRequestHandler):
    "Access a seqrun in a libprep."

    saver = SeqrunSaver

    def get(self, projectid, sampleid, libprepid, seqrunid):
        """Return the seqrun data.
        Return HTTP 404 if no such seqrun, libprep, sample or project."""
        seqrun = self.get_seqrun(projectid, sampleid, libprepid, seqrunid)
        if not seqrun: return
        self.add_seqrun_links(seqrun)
        self.write(seqrun)

    def put(self, projectid, sampleid, libprepid, seqrunid):
        """Update the seqrun data.
        Return HTTP 204 "No Content".
        Return HTTP 404 if no such seqrun, libprep, sample or project.
        Return HTTP 400 if any problem with a value."""
        seqrun = self.get_seqrun(projectid, sampleid, libprepid, seqrunid)
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with self.saver(doc=seqrun, rqh=self) as saver:
                    saver.store(data=data)
            except ValueError, msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                self.set_status(204)


class ApiSeqrunCreate(ApiRequestHandler):
    "Create a seqrun within a libprep."

    saver = SeqrunSaver

    def post(self, projectid, sampleid, libprepid):
        """Create a seqrun within a libprep.
        Return HTTP 201, seqrun URL in header "Location", and seqrun data.
        Return HTTP 400 if something is wrong with the values.
        Return HTTP 404 if no such project, sample or libprep.
        Return HTTP 409 if there is a document revision conflict."""
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with self.saver(rqh=self, libprep=libprep) as saver:
                    saver.store()
                    seqrun = saver.doc
            except ValueError, msg:
                raise tornado.web.HTTPError(400, reason=str(msg))
            except IOError, msg:
                raise tornado.web.HTTPError(409, reason=str(msg))
            else:
                url = self.reverse_url('api_seqrun',
                                       projectid,
                                       sampleid,
                                       libprepid,
                                       seqrun['seqrunid'])
                self.set_header('Location', url)
                self.set_status(201)
                self.add_seqrun_links(seqrun)
                self.write(seqrun)


class ApiProjectSeqruns(ApiRequestHandler):
    "Access to all seqruns for a project."

    def get(self, projectid):
        "Return list of all seqruns for the given project."
        self.write(dict(seqruns=self.get_seqruns(projectid)))

    def get_seqruns(self, projectid, sampleid='', libprepid=''):
        seqruns = self.get_seqruns(projectid, sampleid, libprepid)
        for seqrun in seqruns:
            self.add_seqrun_links(seqrun)
        return seqruns


class ApiSampleSeqruns(ApiProjectSeqruns):
    "Access to all seqruns for a sample."

    def get(self, projectid, sampleid):
        "Return list of all seqruns for the given sample and project."
        self.write(dict(seqruns=self.get_seqruns(projectid, sampleid)))


class ApiLibprepSeqruns(ApiProjectSeqruns):
    "Access to all seqruns for a libprep."

    def get(self, projectid, sampleid, libprepid):
        "Return list of all seqruns for the given libprep, sample and project."
        self.write(dict(seqruns=self.get_seqruns(projectid, sampleid, libprepid)))
