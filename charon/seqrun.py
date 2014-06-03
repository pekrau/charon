" Charon: Seqrun interface. "

import logging
import json

import tornado.web
import couchdb

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .api import ApiRequestHandler
from .libprep import LibprepSaver


class ApiSeqrun(ApiRequestHandler):
    "Access and update a seqrun in a libprep."

    def get(self, projectid, sampleid, libprepid, seqrunid):
        "Return the seqrun data."
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        if not libprep: return
        try:
            pos = int(seqrunid)
            if pos <= 0: raise ValueError
            seqrun = libprep['seqruns'][pos - 1]
        except (TypeError, ValueError, IndexError):
            self.send_error(404, reason='no such item')
        else:
            self.write(seqrun)

    def put(self, projectid, sampleid, libprepid, seqrunid):
        "Update the seqrun data. XXX to be implemented"
        raise NotImplementedError


class SeqrunCreate(RequestHandler):
    "Create a seqrun within a libprep."

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid):
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        self.render('seqrun_create.html',
                    project=project,
                    sample=sample,
                    libprep=libprep)

    @tornado.web.authenticated
    def post(self, projectid, sampleid, libprepid):
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            with LibprepSaver(doc=libprep, rqh=self) as saver:
                seqrun = dict(status=self.get_argument('status', None))
                saver['seqruns'] = libprep['seqruns'] + [seqrun]
        except ValueError, msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except IOError, msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        url = self.reverse_url('libprep', projectid, sampleid, libprepid)
        self.redirect(url)


class ApiSeqrunCreate(ApiRequestHandler):
    "Create a seqrun within a libprep."

    def post(self, projectid, sampleid, libprepid):
        """Create a seqrun within a libprep.
        JSON data:
          status (required)
          alignment_status (optional)
          alignment_coverage (optional) in percent, float (max 100)
          pos (computed) number of seqrun within libprep
        Redirect to libprep URL.
        Return HTTP 400 if something is wrong with the values.
        Return HTTP 409 if there is a document revision conflict."""
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with LibprepSaver(doc=libprep, rqh=self) as saver:
                    seqrun = dict(status=data.get('status'),
                                  alignment_status=data.get('alignment_status'),
                                  alignment_coverage=data.get('alignment_coverage'),
                                  pos=len(libprep['seqruns']))
                    saver['seqruns'] = libprep['seqruns'] + [seqrun]
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


class SeqrunEdit(RequestHandler):
    "Edit an existing seqrun."

    @tornado.web.authenticated
    def get(self, projectid, sampleid, libprepid, seqrunid):
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            seqrunpos = int(seqrunid) - 1
        except (TypeError, ValueError):
            raise tornado.web.HTTPError(404, reason='no such seqrun')
        self.render('seqrun_edit.html', libprep=libprep, seqrunpos=seqrunpos)

    @tornado.web.authenticated
    def post(self, projectid, sampleid, libprepid, seqrunid):
        self.check_xsrf_cookie()
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            pos = int(seqrunid) - 1
            libprep['seqruns'][pos]
        except (TypeError, ValueError, IndexError):
            raise tornado.web.HTTPError(404, reason='no such seqrun')
        try:
            with LibprepSaver(doc=libprep, rqh=self) as saver:
                saver.update()
        except ValueError, msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except IOError, msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        else:
            url = self.reverse_url('libprep', projectid, sampleid, libprepid)
            self.redirect(url)
