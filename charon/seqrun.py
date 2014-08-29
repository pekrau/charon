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

from .sample import SampleSaver

class SeqrunidField(IdField):
    "The unique identifier for the seqrun within the project."

    def check_valid(self, saver, value):
        "Also check uniqueness."
        if not constants.RID_RX.match(value):
            raise ValueError('invalid identifier value (disallowed characters)')
        key = saver.libprep['libprepid']+ value
        view = saver.db.view('seqrun/seqrunid')
        if len(list(view[key])) > 0:
            raise ValueError('not unique')




class SeqrunSaver(Saver):
    "Saver and fields definitions for the seqrun entity."

    doctype = constants.SEQRUN

    fields = [SeqrunidField('seqrunid'),
              SelectField('sequencing_status', description='The status of the sequencing.',
                          options=constants.BASE_STATUS),
              SelectField('alignment_status', description='The status of the alignment.',
                          options=constants.BASE_STATUS),
              Field('runid',
                    description='The flowcell+lane identifier.'),
              Field('seq_qc_flag',
                    description='QC flag of the sequencing process'),
              Field('demux_qc_flag',
                    description='QC flqg of the demultiplex run'),
              Field('mean_coverage',
                    description='Mean coverage'),
              Field('std_coverage',
                    description='standard coverage.'),
              Field('GC_percentage',
                    description='percentage of G & C'),
              Field('aligned_bases',
                    description='Number of aligned bases'),
              Field('mapped_bases',
                    description='Number of mapped bases'),
              Field('mapped_reads',
                    description='Number of mapped reads'),
              FloatField('total_reads',
                    description='Number of reads. Cannot be None, Must be at least 0', default=0),
              Field('reads_per_lane',
                  description='dictionnary of "<lane number>" : "<reads number>"' ),
              Field('sequenced_bases',
                    description='Number of sequenced bases'),
              Field('windows',
                    description='Number of windows'),
              Field('bam_file',
                    description='path of the bam file'),
              Field('output_file',
                    description='path of the output file'),
              Field('mean_mapping_quality',
                    description='mean mapping quality'),
              Field('bases_number',
                    description='number of bases'),
              Field('contigs_number',
                    description='number of contigs'),
              FloatField('mean_autosomal_coverage',
                    description='mean autosomal coverage', default=0),
              FloatField('lanes',
                    description='number of lanes'),
              #RangeFloatField('alignment_coverage', 
              #                minimum=0.0,
              #                description='The coverage of the reference'
              #                ' genome, in percent. Cannot be None, Must be at least 0'),
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
                self.update_sample_cov(projectid,sampleid) 
                
    def update_sample_cov(self, projectid, sampleid):
        """this calculates the total of each mean autosomalcoverage and updates sample leve.
        This should be done every time a seqrun is updated/created
        This also updated total_sequenced_reads"""
        try:
            seqruns = self.get_seqruns(projectid, sampleid)
            totalcov=0
            totalreads=0
            for seqrun in seqruns:
                if seqrun.get('mean_autosomal_coverage'):
                    totalcov+=float(seqrun['mean_autosomal_coverage'])
                if seqrun.get('total_reads'):
                    totalreads+=float(seqrun['total_reads'])
            
            doc= self.get_sample(projectid, sampleid)

            doc['total_autosomal_coverage']=totalcov
            doc['total_sequenced_reads']=totalreads
            logging.info(doc)
        except Exception, msg:
            self.send_error(400, reason=str("Failed to update total_autosomal_coverage and total_sequenced_reads. Check that the reads field and the mean_autosomal_coverage field are not set to None"+msg))
        except IOError, msg:
            self.send_error(409, reason=str(msg))
        else:
            try:
                with SampleSaver(doc=doc, rqh=self) as saver:
                    saver.store(data=doc)#failing to provide data will end up in an empty record.
            except ValueError, msg:
                self.send_error(400, reason=str("failed to update sample "+msg))
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
                    saver.store(data=data)
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
                self.update_sample_cov(projectid, sampleid)
                self.set_header('Location', url)
                self.set_status(201)
                self.add_seqrun_links(seqrun)
                self.write(seqrun)

                
    def update_sample_cov(self, projectid, sampleid):
        """this calculates the total of each mean autosomal coverage and updates sample leve.
        This should be done every time a seqrun is updated/created"""
        logging.debug('Updating total_sequenced_reads and total_autosomal_coverage of sample {0}'.format(sampleid))    
        try:
            seqruns = self.get_seqruns(projectid, sampleid)
            totalcov=0
            totalreads=0
            for seqrun in seqruns:
                if seqrun['mean_autosomal_coverage']:
                    totalcov+=float(seqrun['mean_autosomal_coverage'])
                if seqrun['total_reads']:
                    totalreads+=float(seqrun['total_reads'])
            
            doc= self.get_sample(projectid, sampleid)

            doc['total_autosomal_coverage']=totalcov
            doc['total_sequenced_reads']=totalreads
        except Exception, msg:
            self.send_error(400, reason=str(msg))
        except IOError, msg:
            self.send_error(409, reason=str(msg))
        else:
            try:
                with SampleSaver(doc=doc, rqh=self) as saver:
                    saver.store(data=doc)#failing to provide data will end up in an empty record.
            except ValueError, msg:
                self.send_error(400, reason=str("Failed to update total_autosomal_coverage and total_sequenced_reads. Check that the reads field and the mean_autosomal_coverage field are not set to None"+msg))
            except IOError, msg:
                self.send_error(409, reason=str(msg))
            else:
                self.set_status(201)




class ApiProjectSeqruns(ApiRequestHandler):
    "Access to all seqruns for a project."

    def get(self, projectid):
        "Return list of all seqruns for the given project."
        seqruns = self.get_seqruns(projectid)
        for seqrun in seqruns:
            self.add_seqrun_links(seqrun)
        self.write(dict(seqruns=seqruns))


class ApiSampleSeqruns(ApiRequestHandler):
    "Access to all seqruns for a sample."

    def get(self, projectid, sampleid):
        "Return list of all seqruns for the given sample and project."
        seqruns = self.get_seqruns(projectid, sampleid)
        for seqrun in seqruns:
            self.add_seqrun_links(seqrun)
        self.write(dict(seqruns=seqruns))


class ApiLibprepSeqruns(ApiRequestHandler):
    "Access to all seqruns for a libprep."

    def get(self, projectid, sampleid, libprepid):
        "Return list of all seqruns for the given libprep, sample and project."
        seqruns = self.get_seqruns(projectid, sampleid, libprepid)
        for seqrun in seqruns:
            self.add_seqrun_links(seqrun)
        self.write(dict(seqruns=seqruns))
