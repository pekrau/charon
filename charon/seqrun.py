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
                                            type='auto',
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


class SeqrunSaver(Saver):
    "Saver and fields definitions for the seqrun entity."

    doctype = constants.SEQRUN

    fields = [SeqrunidField('seqrunid'),
              Field('status', description='The status of the seqrun.'),
              Field('runid',
                    description='The identifier for the flowcell and lane.'),
              Field('alignment_status',
                    description='Status of the alignment of data to the reference genome.'),
              Field('alignment_coverage', 
                    description='The coverage of the reference genome, in percent.'),
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


class SeqrunCreate(RequestHandler):
    "Create a seqrun within a libprep."

    saver = SeqrunSaver

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid):
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        self.render('seqrun_create.html',
                    project=project,
                    sample=sample,
                    libprep=libprep,
                    fields=self.saver.fields)

    @tornado.web.authenticated
    def post(self, projectid, sampleid, libprepid):
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            with self.saver(rqh=self, libprep=libprep) as saver:
                saver.store(None)
                seqrun = saver.seqrun
        except (IOError, ValueError), msg:
            self.render('seqrun_create.html',
                        project=project,
                        sample=sample,
                        libprep=libprep,
                        fields=self.saver.fields,
                        error=str(error))
        else:
            url = self.reverse_url('seqrun', projectid, sampleid, libprepid,)
            self.redirect(url)


class SeqrunEdit(RequestHandler):
    "Edit an existing seqrun."

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid, seqrunid):
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            seqrunid = int(seqrunid)
            if seqrunid <= 0: raise ValueError
            if seqrunid > len(libprep['seqruns']): raise ValueError
        except (TypeError, ValueError):
            raise tornado.web.HTTPError(404, reason='no such seqrun')
        self.render('seqrun_edit.html', libprep=libprep, seqrunid=seqrunid)

    @tornado.web.authenticated
    def post(self, projectid, sampleid, libprepid, seqrunid):
        self.check_xsrf_cookie()
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            pos = int(seqrunid) - 1
            if pos < 0: raise ValueError
            if pos >= len(libprep['seqruns']): raise ValueError
        except (TypeError, ValueError):
            raise tornado.web.HTTPError(404, reason='no such seqrun')
        try:
            with LibprepSaver(doc=libprep, rqh=self) as saver:
                saver.update_seqrun(pos)
        except ValueError, msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except IOError, msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        else:
            url = self.reverse_url('libprep', projectid, sampleid, libprepid)
            self.redirect(url)


class ApiSeqrun(ApiRequestHandler):
    "Access a seqrun in a libprep."

    def get(self, projectid, sampleid, libprepid, seqrunid):
        """Return the seqrun data.
        Return HTTP 404 if no such seqrun, libprep, sample or project."""
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        if not libprep: return
        try:
            pos = int(seqrunid) - 1
            if pos < 0: raise ValueError
            seqrun = libprep['seqruns'][pos]
        except (TypeError, ValueError, IndexError):
            self.send_error(404, reason='no such seqrun')
        else:
            self.write(seqrun)

    def put(self, projectid, sampleid, libprepid, seqrunid):
        """Update the seqrun data.
        Return HTTP 204 "No Content".
        Return HTTP 404 if no such seqrun, libprep, sample or project.
        Return HTTP 400 if any problem with a value."""
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            pos = int(seqrunid) - 1
            if pos < 0: raise ValueError
            if pos >= len(libprep['seqruns']): raise ValueError
        except (ValueError, TypeError):
            self.send_error(404, reason='no such seqrun')
        else:
            try:
                data = json.loads(self.request.body)
            except Exception, msg:
                self.send_error(400, reason=str(msg))
            else:
                with LibprepSaver(doc=libprep, rqh=self) as saver:
                    saver.update_seqrun(pos, seqrun=data)
                self.set_status(204)


class ApiSeqrunCreate(ApiRequestHandler):
    "Create a seqrun within a libprep."

    def post(self, projectid, sampleid, libprepid):
        """Create a seqrun within a libprep.
        JSON data:
          status (required)
          alignment_status (optional)
          alignment_coverage (optional), float (min 0.0)
        Return 204 "No content" and (NOTE!) libprep URL in header.
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
                with LibprepSaver(doc=libprep, rqh=self) as saver:
                    saver.update_seqrun(None)
            except ValueError, msg:
                raise tornado.web.HTTPError(400, reason=str(msg))
            except IOError, msg:
                raise tornado.web.HTTPError(409, reason=str(msg))
            else:
                logging.debug("created seqrun %i %s",
                              len(libprep['seqruns']),
                              libprep['libprepid'])
                url = self.reverse_url('api_libprep',
                                       projectid,
                                       sampleid,
                                       libprepid)
                self.set_header('Location', url)
                self.set_status(204)
