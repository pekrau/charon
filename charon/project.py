" Charon: Project entity interface. "

import logging
import json
import csv
import cStringIO

import tornado.web
import couchdb

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .api import ApiRequestHandler
from .saver import *
from .sample import SampleSaver


class ProjectidField(IdField):
    "The unique identifier for the project, e.g. 'P1234'."

    def check_valid(self, saver, value):
        "Also check uniqueness."
        super(ProjectidField, self).check_valid(saver, value)
        view = saver.db.view('project/projectid')
        if len(list(view[value])) > 0:
            raise ValueError('not unique')


class ProjectnameField(NameField):
    """The name of the project, e.g. 'P.Kraulis_14_01'.
    Optional; must be unique if given."""

    def check_valid(self, saver, value):
        "Also check uniqueness."
        super(ProjectnameField, self).check_valid(saver, value)
        if saver.get(self.key) == value: return
        view = saver.db.view('project/name')
        if len(list(view[value])) > 0:
            raise ValueError('not unique')


class ProjectSaver(Saver):
    "Saver and fields definitions for the project entity."

    doctype = constants.PROJECT

    fields = [ProjectidField('projectid', title='Identifier'),
              ProjectnameField('name'),
              SelectField('status', description='The status of the project.',
                          options=constants.PROJECT_STATUS),
              Field('pipeline',
                    description='Pipeline to use for project data analysis.'),
              Field('reference',
                    description='Reference sequence to be used'),
              Field('best_practice_analysis',
                    title='Best-practice analysis',
                    description='Status of best-practice analysis.'),
              SelectField('sequencing_facility',
                          options=constants.SEQ_FACILITIES,
                          description='The location of the samples')
              ]


class UploadSamplesMixin(object):
    """Mixin providing a method to upload samples from a CSV file.
    Samples are created, not updated.
    The input is sample identifiers only.
    """

    def upload_samples(self, project):
        "Upload samples from file provided via HTML form field."
        samples = []
        try: 
            data = self.request.files['csvfile'][0]
        except (KeyError, IndexError):
            raise tornado.web.HTTPError(400, reason='no CSV file uploaded')
        self.messages = ["Data from file {0}".format(data['filename'])]
        self.errors = []
        samples_set = set()
        view = self.db.view('sample/sampleid',
                            startkey=[project['projectid'], ''],
                            endkey=[project['projectid'], constants.HIGH_CHAR])
        for row in view:
            sampleid = row.key[1]
            if sampleid in samples_set:
                self.errors.append("sampleid '{0}' defined multiple times?".
                                   format(sampleid))
            else:
                samples_set.add(sampleid)
        reader = csv.reader(cStringIO.StringIO(data['body']))
        # First get all new sampleids, and check uniqueness
        for pos, record in enumerate(reader):
            try:
                sampleid = record[0].strip()
                if not sampleid:
                    raise IndexError
                if sampleid in samples_set:
                    raise KeyError
                samples_set.add(sampleid)
                samples.append(sampleid)
            except IndexError:
                self.errors.append("line {0}: empty record".format(pos+1))
            except KeyError:
                self.errors.append("line {0}: non-unique sampleid {1}".
                                   format(pos+1, sampleid))
            if len(self.errors) > 10:
                self.errors.append('too many errors, giving up...')
                break
        if self.errors:
            self.messages.append('No samples added.')
        else:
            # Add samples when no previous errors
            for pos, sampleid in enumerate(samples):
                try:
                    with SampleSaver(rqh=self, project=project) as saver:
                        data = dict(sampleid=sampleid)
                        saver.store(data=data)
                except (IOError, ValueError), msg:
                    self.errors.append("line {0}: {1}".format(pos+1, str(msg)))
            self.messages.append("{0} samples added".format(len(samples)))


class UpdateSamplesMixin(object):
    """Mixin providing a method to update sample information from a CSV file.
    Samples are updated, not created.
    The input must contain the sample identifier.
    All other columns (fields) are optional.
    """

    def update_samples(self, project):
        "Update samples from a file provided via HTML form field."
        try: 
            data = self.request.files['csvfile'][0]
        except (KeyError, IndexError):
            raise tornado.web.HTTPError(400, reason='no CSV file uploaded')
        self.messages = ["Data from file {0}".format(data['filename'])]
        self.errors = []
        reader = csv.reader(cStringIO.StringIO(data['body']))
        # Header: get positions of fields
        header = reader.next()
        lookup = dict()
        for field in SampleSaver.fields:
            try:
                lookup[field.key] = header.index(field.key)
            except ValueError:
                if field.key == 'sampleid':
                    self.errors.append("column 'sampleid' is missing")
        rows = list(reader)
        if 'sampleid' in lookup:
            # First just check
            for pos, row in enumerate(rows):
                # Check that the sample identifiers match existing samples
                try:
                    sampleid = row[lookup['sampleid']].strip()
                    if not sampleid: raise ValueError
                except (IndexError, ValueError):
                    self.errors.append("line {0}; no sampleid".format(pos+1))
                    continue
                try:
                    sample = self.get_sample(project['projectid'], sampleid)
                except tornado.web.HTTPError:
                    self.errors.append("line {0}; no such sample '{1}'".
                                       format(pos+1, sampleid))
                    continue
                # Collect update data for sample
                data = dict()
                for key, slot in lookup.iteritems():
                    if key == 'sampleid': continue
                    value = row[slot].strip()
                    if not value: continue
                    data[key] = value
                # Check that update of sample is valid
                try:
                    with SampleSaver(rqh=self, doc=sample) as saver:
                        saver.store(data=data, check_only=True)
                except ValueError, msg:
                    self.errors.append("row {0}; {1}".format(pos+1, str(msg)))
        if self.errors:
            self.messages.append('No samples added.')
        else:
            # And now actually do it...
            for row in rows:
                sampleid = row[lookup['sampleid']].strip()
                sample = self.get_sample(project['projectid'], sampleid)
                # Collect update data for sample
                data = dict()
                for key, slot in lookup.iteritems():
                    if key == 'sampleid': continue
                    value = row[slot].strip()
                    if not value: continue
                    data[key] = value
                # Store it 
                with SampleSaver(rqh=self, doc=sample) as saver:
                    saver.store(data=data)
            self.messages.append("{0} samples updated.".format(len(rows)))


class Project(RequestHandler):
    "Display the project data."

    saver = ProjectSaver

    @tornado.web.authenticated
    def get(self, projectid):
        "Display the project information."
        project = self.get_project(projectid)
        projectid=project['projectid']
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


class ProjectUpload(UploadSamplesMixin, RequestHandler):
    "Upload samples into the project."

    @tornado.web.authenticated
    def get(self, projectid):
        "Display the project samples upload form."
        project = self.get_project(projectid)
        self.render('project_upload.html',
                    project=project,
                    message=self.get_argument('message', None),
                    error=self.get_argument('error', None))

    @tornado.web.authenticated
    def post(self, projectid):
        "Edit the project with the given form data."
        self.check_xsrf_cookie()
        project = self.get_project(projectid)
        self.upload_samples(project)
        url = self.get_absolute_url('project_upload', project['projectid'],
                                    message='\n'.join(self.messages),
                                    error='\n'.join(self.errors))
        self.redirect(url)


class ProjectUpdate(UpdateSamplesMixin, RequestHandler):
    """Update sample in the project.
    Data from CSV file having headers which defined which field to update.
    """

    @tornado.web.authenticated
    def get(self, projectid):
        "Display the project samples update form."
        project = self.get_project(projectid)
        self.render('project_samples_update.html',
                    project=project,
                    samplesaver=SampleSaver,
                    message=self.get_argument('message', None),
                    error=self.get_argument('error', None))

    @tornado.web.authenticated
    def post(self, projectid):
        "Edit the project with the given form data."
        self.check_xsrf_cookie()
        project = self.get_project(projectid)
        self.update_samples(project)
        url = self.get_absolute_url('project_update',
                                    project['projectid'],
                                    message='\n'.join(self.messages),
                                    error='\n'.join(self.errors))
        self.redirect(url)

    

class Projects(RequestHandler):
    "List all projects."

    @tornado.web.authenticated
    def get(self):
        projects = self.get_projects()
        self.render('projects.html', projects=projects)


class ApiProject(UploadSamplesMixin, ApiRequestHandler):
    "Access a project."

    saver = ProjectSaver

    # Do not use authentication decorator; do not send to login page, but fail.
    def get(self, projectid):
        """Return the project data as JSON.
        Return HTTP 404 if no such project."""
        project = self.get_project(projectid)
        if not project: return
        self.add_project_links(project)
        self.write(project)

    # Do not use authentication decorator; do not send to login page, but fail.
    def post(self, projectid): 
        "Upload a CSV file containing identifiers of samples to create."
        project = self.get_project(projectid)
        self.upload_samples(project)
        self.write(dict(errors=self.errors, messages=self.messages))
        if self.errors:
            self.set_status(400)

    # Do not use authentication decorator; do not send to login page, but fail.
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
            logging.debug("Exception: %s", msg)
            self.send_error(400, reason=str(msg))
        else:
            try:
                with self.saver(doc=project, rqh=self) as saver:
                    saver.store(data=data)
            except ValueError, msg:
                logging.debug("ValueError: %s", msg)
                self.send_error(400, reason=str(msg))
            except IOError, msg:
                logging.debug("IOError: %s", msg)
                self.send_error(409, reason=str(msg))
            else:
                self.set_status(204)

    # Do not use authentication decorator; do not send to login page, but fail.
    def delete(self, projectid):
        """NOTE: This is for unit test purposes only!
        Delete the project and all of its dependent entities.
        Returns HTTP 204 "No Content"."""
        project = self.get_project(projectid)
        if not project: return
        utils.delete_project(self.db, project)
        logging.debug("deleted project %s", projectid)
        self.set_status(204)


class ApiProjectSamplesUpdate(UpdateSamplesMixin, ApiRequestHandler):
    "Update samples in a project."

    saver = ProjectSaver

    # Do not use authentication decorator; do not send to login page, but fail.
    def post(self, projectid): 
        "Upload a CSV file containing identifiers of samples to create."
        project = self.get_project(projectid)
        self.update_samples(project)
        self.write(dict(errors=self.errors, messages=self.messages))
        if self.errors:
            self.set_status(400)


class ApiProjectCreate(ApiRequestHandler):
    "Create a new project."

    saver = ProjectSaver

    # Do not use authentication decorator; do not send to login page, but fail.
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

    # Do not use authentication decorator; do not send to login page, but fail.
    def get(self):
        "Return a list of all projects."
        projects = self.get_projects()
        for project in projects:
            self.add_project_links(project)
        self.write(dict(projects=projects))


class ApiProjectsNotDone(ApiRequestHandler):
    "Access to all projects that are not done."

    # Do not use authentication decorator; do not send to login page, but fail.
    def get(self):
        "Return a list of all undone projects."
        projects = self.get_not_done_projects()
        for project in projects:
            self.add_project_links(project)
        self.write(dict(projects=projects))
