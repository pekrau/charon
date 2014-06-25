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
        Return HTTP 404 if no such seqrun, libprep, sample or project.
        Return HTTP 400 if any problem with a value."""
        project = self.get_project(projectid)
        sample = self.get_sample(projectid, sampleid)
        libprep = self.get_libprep(projectid, sampleid, libprepid)
        try:
            pos = int(seqrunid) - 1
            if pos < 0: raise ValueError
            seqrun = libprep['seqruns'][pos]
        except (ValueError, TypeError, IndexError):
            self.send_error(404, reason='no such seqrun')
        else:
            try:
                data = json.loads(self.request.body)
                try:
                    if not isinstance(data['coverage'], (float, int)):
                        raise ValueError('invalid coverage type')
                    if pos != data.pop('pos'):
                        raise ValueError('incorrect pos value')
                except KeyError:
                    pass
            except Exception, msg:
                self.send_error(400, reason=str(msg))
            else:
                seqrun.update(data)
                with LibprepSaver(doc=libprep, rqh=self) as saver:
                    seqruns = libprep['seqruns']
                    seqruns[pos] = seqrun
                    saver['seqruns'] = seqruns
                seqrun['pos'] = pos
                self.write(seqrun)


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
                saver.update_seqrun(None)
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
            libprep['seqruns'][pos]
        except (TypeError, ValueError, IndexError):
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
