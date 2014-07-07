" Charon: Project entity interface. "

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


class ProjectidField(IdField):
    "The unique identifier for the project, e.g. 'P1234'."

    def check_unique(self, saver, value):
        view = saver.db.view('project/projectid')
        if len(list(view[value])) > 0:
            raise ValueError('not unique')


class ProjectnameField(NameField):
    """The name of the project, e.g. 'P.Kraulis_14_01'.
    Optional; must be unique if given."""

    def check_unique(self, saver, value):
        if not value: return
        if saver.get(self.key) == value: return
        view = saver.db.view('project/name')
        if len(list(view[value])) > 0:
            raise ValueError('not unique')


class ProjectSaver(Saver):
    "Saver and fields definitions for the project entity."

    doctype = constants.PROJECT

    fields = [ProjectidField('projectid', title='Identifier'),
              ProjectnameField('name'),
              Field('status', description='The status of the project.'),
              Field('pipeline',
                    description='Pipeline to use for project data analysis.'),
              Field('best_practice_analysis',
                    title='Best-practice analysis',
                    description='Status of best-practice analysis.'),
              ]


class Project(RequestHandler):
    "Display the project data."

    saver = ProjectSaver

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
        logs = self.get_logs(project['_id']) # XXX limit?
        self.render('project.html',
                    project=project,
                    samples=samples,
                    fields=self.saver.fields,
                    logs=logs)


class ProjectCreate(RequestHandler):
    "Create a new project and redirect to it."

    saver = ProjectSaver

    @tornado.web.authenticated
    def get(self):
        "Display the project creation form."
        self.render('project_create.html', fields=self.saver.fields)

    @tornado.web.authenticated
    def post(self):
        """Create the project given the form data.
        Redirect to the project page."""
        self.check_xsrf_cookie()
        try:
            with self.saver(rqh=self) as saver:
                saver.store()
                project = saver.doc
        except (IOError, ValueError), msg:
            self.render('project_create.html',
                        fields=self.saver.fields,
                        error=str(msg))
        else:
            url = self.reverse_url('project', project['projectid'])
            self.redirect(url)


class ProjectEdit(RequestHandler):
    "Edit an existing project."

    saver = ProjectSaver

    @tornado.web.authenticated
    def get(self, projectid):
        "Display the project edit form."
        project = self.get_project(projectid)
        self.render('project_edit.html',
                    project=project,
                    fields=self.saver.fields)

    @tornado.web.authenticated
    def post(self, projectid):
        "Edit the project with the given form data."
        self.check_xsrf_cookie()
        project = self.get_project(projectid)
        try:
            with self.saver(doc=project, rqh=self) as saver:
                saver.store()
        except (IOError, ValueError), msg:
            self.render('project_edit.html',
                        fields=self.saver.fields,
                        project=project,
                        error=str(msg))
        else:
            url = self.reverse_url('project', project['projectid'])
            self.redirect(url)


class Projects(RequestHandler):
    "List all projects."

    @tornado.web.authenticated
    def get(self):
        projects = self.get_projects()
        self.render('projects.html', projects=projects)


class ApiProject(ApiRequestHandler):
    "Access a project."

    saver = ProjectSaver

    def get(self, projectid):
        """Return the project data as JSON.
        Return HTTP 404 if no such project."""
        project = self.get_project(projectid)
        if not project: return
        self.add_project_links(project)
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
                with self.saver(doc=project, rqh=self) as saver:
                    saver.store(data=data)
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


class ApiProjectCreate(ApiRequestHandler):
    "Create a new project."

    saver = ProjectSaver

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
                with self.saver(rqh=self) as saver:
                    saver.store(data=data)
                    project = saver.doc
            except (KeyError, ValueError), msg:
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                projectid = project['projectid']
                url = self.reverse_url('api_project', projectid)
                self.set_header('Location', url)
                self.set_status(201)
                self.add_project_links(project)
                self.write(project)


class ApiProjects(ApiRequestHandler):
    "Access to all projects."

    def get(self):
        "Return a list of all projects."
        projects = self.get_projects()
        for project in projects:
            self.add_project_links(project)
        self.write(dict(projects=projects))
