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
    field_keys = ['projectid', 'name', 'status', 'best_practice_analysis']

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
        self.render('project.html',
                    project=project,
                    samples=samples,
                    logs=self.get_logs(project['_id']))


class ApiProject(ApiRequestHandler):
    "Return the project data, or edit it, or delete the project."

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
        """Update the project fields with the given data.
        Return HTTP 204 "No Content".
        Return HTTP 400 if input data is invalid.
        Return HTTP 404 if no such project.
        Return HTTP 409 if there is a document revision update conflict."""
        project = self.get_project(projectid)
        if not project: return
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.http_error(400, msg)
        else:
            try:
                with ProjectSaver(doc=project, rqh=self) as saver:
                    saver.update(data=data)
            except ValueError, msg:
                self.http_error(400, msg)
            except IOError, msg:
                self.http_error(409, msg)
            else:
                self.set_status(204)

    def delete(self, projectid):
        """Delete the project and all of its dependent entities.
        Returns HTTP 204 "No Content".
        For test purposes only!"""
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
            self.http_error(400, msg)
        except IOError, msg:
            self.http_error(409, msg)
        else:
            url = self.reverse_url('project', project['projectid'])
            self.redirect(url)


class ApiProjectCreate(ApiRequestHandler):
    "Create a new project from the given data."

    def post(self):
        """Create a project from the given JSON data.
        Return HTTP 201 and URL of the project in header "Location".
        Return HTTP 400 if something is wrong with the data."""
        try:
            data = json.loads(self.request.body)
        except Exception, msg:
            self.http_error(400, msg)
        else:
            try:
                with ProjectSaver(rqh=self) as saver:
                    saver.update(data=data)
                    project = saver.doc
            except (KeyError, ValueError), msg:
                self.http_error(400, msg)
            except IOError, msg:
                self.http_error(409, msg)
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
            self.http_error(400, msg)
        except IOError, msg:
            self.http_error(409, msg)
        else:
            self.redirect(self.reverse_url('project', project['projectid']))


class Projects(RequestHandler):
    "List all projects."

    @tornado.web.authenticated
    def get(self):
        projects = self.get_projects()
        self.render('projects.html', projects=projects)


class ApiProjects(ApiRequestHandler):
    "Return a list of all projects."

    def get(self):
        projects = self.get_projects()
        self.write(dict(projects=projects))
