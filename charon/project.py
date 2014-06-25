" Charon: Project interface. "

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


class ProjectSaver(DocumentSaver):
    doctype = constants.PROJECT
    field_keys = ['projectid', 'name', 'status',
                  'best_practice_analysis', 'pipeline']

    def check_projectid(self, value):
        if self.is_new():
            if not value:
                raise ValueError('projectid must have a defined value')
            view = self.db.view('project/projectid')
            rows = list(view[value])
            if len(rows) > 0:
                raise ValueError('projectid is not unique')

    def convert_projectid(self, value):
        "No change allowed after creation."
        if self.is_new():
            return value
        else:
            return self.doc['projectid']

    def check_name(self, value):
        if self.is_new() and value:
            view = self.db.view('project/name')
            rows = list(view[value])
            if len(rows) > 0:
                raise ValueError('name is not unique')

    def convert_status(self, value): return value or None


class Project(RequestHandler):
    "Display the project data."

    @tornado.web.authenticated
    def get(self, projectid):
        "Display the project information."
        project = self.get_project(projectid)
        samples = self.get_samples(projectid)
        view = self.db.view('libprep/count')
        for sample in samples:
            try:
                row = view[[projectid, sample['sampleid']]].rows[0]
            except IndexError:
                sample['libpreps_count'] = 0
            else:
                sample['libpreps_count'] = row.value
        view = self.db.view('seqrun/count')
        for sample in samples:
            try:
                startkey = [projectid, sample['sampleid']]
                endkey = [projectid, sample['sampleid'], constants.HIGH_CHAR]
                row = view[startkey:endkey].rows[0]
            except IndexError:
                sample['seqruns_count'] = 0
            else:
                sample['seqruns_count'] = row.value
        self.render('project.html',
                    project=project,
                    samples=samples,
                    logs=self.get_logs(project['_id']))


class ApiProject(ApiRequestHandler):
    "Access a project."

    def get(self, projectid):
        """Return the project data as JSON.
        Return HTTP 404 if no such project."""
        project = self.get_project(projectid)
        if not project: return
        startkey = (projectid, '')
        endkey = (projectid, constants.HIGH_CHAR)
        project['samples'] = samples = []
        for row in self.db.view('sample/sampleid')[startkey:endkey]:
            sampleid = row.key[1]
            data = dict(sampleid=sampleid,
                        href=self.reverse_url('api_sample',
                                              projectid,
                                              sampleid))
            samples.append(data)
        project['links'] = links = dict()
        links['samples'] = dict(href=self.reverse_url('api_samples', projectid))
        links['logs'] = dict(href=self.reverse_url('api_logs', project['_id']))
        self.write(project)

    def put(self, projectid):
        """Update the project with the given JSON data.
        Return HTTP 204 "No Content" when successful.
        Return HTTP 400 if the input data is invalid.
        Return HTTP 404 if no such project.
        Return HTTP 409 if there is a document revision update conflict."""
        project = self.get_project(projectid)
        if not project: return
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with ProjectSaver(doc=project, rqh=self) as saver:
                    saver.update(data=data)
            except ValueError, msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                self.set_status(204)

    def delete(self, projectid):
        """NOTE: This is for unit test purposes only!
        Delete the project and all of its dependent entities.
        Returns HTTP 204 "No Content"."""
        project = self.get_project(projectid)
        if not project: return
        utils.delete_project(self.db, project)
        logging.debug("deleted project %s", projectid)
        self.set_status(204)


class ProjectCreate(RequestHandler):
    "Create a new project and redirect to it."

    @tornado.web.authenticated
    def get(self):
        "Display the project creation form."
        self.render('project_create.html')

    @tornado.web.authenticated
    def post(self):
        """Create the project given the form data.
        Redirect to the project page.
        Return HTTP 400 if something is wrong with the data."""
        self.check_xsrf_cookie()
        try:
            with ProjectSaver(rqh=self) as saver:
                saver.update()
                project = saver.doc
        except ValueError, msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except IOError, msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        else:
            url = self.reverse_url('project', project['projectid'])
            self.redirect(url)


class ApiProjectCreate(ApiRequestHandler):
    "Create a new project."

    def post(self):
        """Create a project.
        Return HTTP 201, project URL in header "Location", and project data.
        Return HTTP 400 if something is wrong with the input data.
        Return HTTP 409 if there is a document revision conflict."""
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        else:
            try:
                with ProjectSaver(rqh=self) as saver:
                    saver.update(data=data)
                    project = saver.doc
            except (KeyError, ValueError), msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                logging.debug("created project %s", project['projectid'])
                url = self.reverse_url('api_project', project['projectid'])
                self.set_header('Location', url)
                self.set_status(201)
                self.write(project)


class ProjectEdit(RequestHandler):
    "Edit an existing project."

    @tornado.web.authenticated
    def get(self, projectid):
        "Display the project edit form."
        project = self.get_project(projectid)
        self.render('project_edit.html', project=project)

    @tornado.web.authenticated
    def post(self, projectid):
        "Edit the project with the given form data."
        self.check_xsrf_cookie()
        project = self.get_project(projectid)
        try:
            with ProjectSaver(doc=project, rqh=self) as saver:
                saver.update()
        except ValueError, msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except IOError, msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        else:
            self.redirect(self.reverse_url('project', project['projectid']))


class Projects(RequestHandler):
    "List all projects."

    @tornado.web.authenticated
    def get(self):
        projects = self.get_projects()
        self.render('projects.html', projects=projects)


class ApiProjects(ApiRequestHandler):
    "Access to all projects."

    def get(self):
        "Return a list of all projects."
        projects = self.get_projects()
        self.write(dict(projects=projects))
