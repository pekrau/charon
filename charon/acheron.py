import sys
import os
import codecs
from optparse import OptionParser
from pprint import pprint
from genologics.entities import *
from genologics.lims import *
from genologics.config import BASEURI, USERNAME, PASSWORD
from datetime import date
import scilifelab.log
import yaml
import inspect
import requests
import json
from types import *
import logging
import pdb

lims = Lims(BASEURI, USERNAME, PASSWORD)
INITIALQC ={'63' : 'Quant-iT QC (DNA) 4.0',
    '66' : 'Qubit QC (DNA) 4.0',
    '24' : 'Customer Gel QC',
    '20' : 'CaliperGX QC (DNA)',
    '16' : 'Bioanalyzer QC (DNA) 4.0',
    '504' : 'Volume Measurement QC'}
AGRINITQC = {'7' : 'Aggregate QC (DNA) 4.0'}
POOLING = {
    '404': "Pre-Pooling (Illumina SBS) 4.0",
    '506': "Pre-Pooling (MiSeq) 4.0"
    }
PREPSTART = {    '117' : 'Applications Generic Process',
    '33' : 'Fragment DNA (TruSeq DNA) 4.0'
            }
PREPEND = {'157': 'Applications Finish Prep',
    '406' : 'End repair, size selection, A-tailing and adapter ligation (TruSeq PCR-free DNA) 4.0'
        }
LIBVAL = {'62' : 'qPCR QC (Library Validation) 4.0',
    '64' : 'Quant-iT QC (Library Validation) 4.0',
    '67' : 'Qubit QC (Library Validation) 4.0',
    '20' : 'CaliperGX QC (DNA)',
    '17' : 'Bioanalyzer QC (Library Validation) 4.0'}
SEQSTART = {'23':'Cluster Generation (Illumina SBS) 4.0',
    '26':'Denature, Dilute and Load Sample (MiSeq) 4.0'}
DILSTART = {'40' : 'Library Normalization (MiSeq) 4.0',
    '39' : 'Library Normalization (Illumina SBS) 4.0'}
SEQUENCING = {'38' : 'Illumina Sequencing (Illumina SBS) 4.0',
    '46' : 'MiSeq Run (MiSeq) 4.0'}
WORKSET = {'204' : 'Setup Workset/Plate'}
SUMMARY = {'356' : 'Project Summary 1.3'}
DEMULTIPLEX={'666' : 'Bcl Conversion & Demultiplexing (Illumina SBS) 4.0'}

def main(options):
    if options.dummy:
        projs=['A.Wedell_13_03', 'G.Grigelioniene_14_01', 'M.Kaller_14_05', 'M.Kaller_14_06', 'M.Kaller_14_08']
        for p in projs:
            cleanCharon(p, options)
            data=prepareData(p)
            writeProjectData(data, options)
        addFakeData(options)
    elif options.all:
        projs=findprojs('all')
        for p in projs:
            cleanCharon(p, options)
            data=prepareData(p)
            writeProjectData(data, options)

    elif options.new:
        projs=findprojs('all')
        for p in projs:
            newdata=prepareData(p)
            olddata=getCompleteProject(newdata['projectid'], options)
            compareOldAndNew(olddata, newdata, options)
        
def compareOldAndNew(old, new, options):
    autoupdate=False
    if old == None:
        writeProjectData(new, options)
        print "updating {}".format(old)
    else:
        newsamples=new['samples']
        oldsamples=old['samples']
        for sampleid in newsamples:
            sample=newsamples[sampleid]
            libs=sample.pop('libs')

            if sampleid not in oldsamples:
                print "updating {}".format(sampleid)
                writeToCharon(json.dumps(sample),'{0}/api/v1/sample/{1}'.format(options.url, new['projectid']), options)
                autoupdate=True
                
            for libid in libs:
                lib=libs[libid]
                seqruns=lib.pop('seqruns')

                if autoupdate or libid not in oldsamples[sampleid]['libs']:  
                    print "updating {} {}".format(sampleid, libid)
                    writeToCharon(json.dumps(lib),'{0}/api/v1/libprep/{1}/{2}'.format(options.url, new['projectid'], sampleid), options)
                    autoupdate=True

                for seqrunid in seqruns:
                    seqrun=seqruns[seqrunid]
                    if autoupdate or seqrunid not in oldsamples[sampleid]['libs'][libid]['seqruns']:
                        print "updating {} {} {}".format(sampleid, libid, seqrunid)
                        writeToCharon(json.dumps(seqrun),'{0}/api/v1/seqrun/{1}/{2}/{3}'.format(options.url, new['projectid'], sampleid, libid), options)


def getCompleteProject(projectid, options):
    session = requests.Session()
    headers = {'X-Charon-API-token': options.token, 'content-type': 'application/json'}
    rq=session.get('{0}/api/v1/project/{1}'.format(options.url, projectid), headers=headers)
    if rq.status_code == 200:
        project=rq.json()
        rq=session.get('{0}/api/v1/samples/{1}'.format(options.url, projectid), headers=headers)
        samples=rq.json()
        project['samples']={}
        for sample in samples['samples']:
            rq=session.get('{0}/api/v1/libpreps/{1}/{2}'.format(options.url, projectid, sample['sampleid']), headers=headers)
            libpreps=rq.json()
            sample['libs']={}
            for libprep in libpreps['libpreps']:
                rq=session.get('{0}/api/v1/seqruns/{1}/{2}/{3}'.format(options.url, projectid, sample['sampleid'], libprep['libprepid']), headers=headers)
                seqruns=rq.json()
                libprep['seqruns']={}
                for seqrun in seqruns['seqruns']:
                    libprep['seqruns'][seqrun['seqrunid']]=seqrun

                sample['libs'][libprep['libprepid']]=libprep

            project['samples'][sample['sampleid']]=sample

        return project
    return None
        
def findprojs(key):
    if key == 'all':
        udf={'Bioinformatic QC':'WG re-seq (IGN)'}
        projects=lims.get_projects(udf=udf)
        return [p.name for p in projects]

def updateCharon(jsonData, url, options):
    if options.fake:
        print "data {}".format(jsonData)
        print "url {}".format(url)
    else:
        session = requests.Session()
        headers = {'X-Charon-API-token': options.token, 'content-type': 'application/json'}
        r=session.put(url, headers=headers, data=jsonData)
        if options.verbose:
            print url
            print jsonData
            if r.status_code==201:
                print "update ok"
            elif r.status_code==400:
                print "input data is wrong, {}".format(r.reason)
            elif r.status_code==409:
                print "Document is being updated"
            else:
                print "Unkown error : {} {}".format(r.status_code, r.text)
 
def writeToCharon(jsonData, url, options):
    if options.fake:
        print "data {}".format(jsonData)
        print "url {}".format(url)
    else:
        session = requests.Session()
        headers = {'X-Charon-API-token': options.token, 'content-type': 'application/json'}
        r=session.post(url, headers=headers, data=jsonData)
        if options.verbose:
            print url
            print jsonData
            if r.status_code==204:
                print "update ok"
            elif r.status_code==400:
                print "input data is wrong, {}".format(r.reason)
            elif r.status_code==409:
                print "Document is being updated"
            else:
                print "Unkown error : {} {}".format(r.status_code, r.text)
 
def writeProjectData(data, options):
    project=data
    samples=project.pop('samples', None)
    url=options.url+'/api/v1/project'
    projson=json.dumps(project)
    writeToCharon(projson, url, options) 
    for sid in samples:
        libs=samples[sid].pop('libs', None)
        sampjson=json.dumps(samples[sid])
        url=options.url+'/api/v1/sample/'+project['projectid']
        writeToCharon(sampjson, url, options)
        for lib in libs:
            seqruns=libs[lib].pop('seqruns', None)
            libjson=json.dumps(libs[lib])
            url=options.url+'/api/v1/libprep/'+project['projectid']+"/"+sid
            writeToCharon(libjson, url, options)
            for seqrun in seqruns:
                seqjson=json.dumps(seqruns[seqrun])
                url=options.url+'/api/v1/seqrun/'+project['projectid']+"/"+sid+"/"+lib
                writeToCharon(seqjson, url, options)
            
def addFakeData(options):

    #adds seqrun data for a.wedell_13_03

    url=options.url+"/api/v1/seqrun/P567/P567_101/A"
    data='{"sequencing_status": "DONE", "demux_qc_flag": "PASSED", "seqrunid": "130611_SN7001298_0148_AH0CCVADXX","seq_qc_flag": "PASSED", "mean_autosomal_coverage": 0, "total_reads": 693366930.0}'
    writeToCharon(data, url, options)
    data='{"sequencing_status": "DONE", "demux_qc_flag": "PASSED", "seqrunid": "130612_D00134_0019_AH056WADXX","seq_qc_flag": "PASSED", "mean_autosomal_coverage": 0, "total_reads": 606139580.0}'
    writeToCharon(data, url,options )
    url=options.url+"/api/v1/seqrun/P567/P567_102/A"
    data='{"sequencing_status": "DONE", "demux_qc_flag": "PASSED","seqrunid": "130627_D00134_0023_AH0JYUADXX", "seq_qc_flag": "PASSED", "mean_autosomal_coverage": 0, "total_reads": 292171094.0}'
    writeToCharon(data, url, options)
    data='{"sequencing_status": "DONE", "demux_qc_flag": "PASSED","seqrunid": "130701_SN7001298_0152_AH0J92ADXX", "seq_qc_flag": "PASSED", "mean_autosomal_coverage": 0, "total_reads": 365307556.0}'
    writeToCharon(data, url, options)
    data='{"sequencing_status": "DONE", "demux_qc_flag": "PASSED","seqrunid": "130701_SN7001298_0153_BH0JMGADXX", "seq_qc_flag": "PASSED", "mean_autosomal_coverage": 0, "total_reads": 356267058.0}    '
    writeToCharon(data, url, options)


def prepareData(projname):

    data={}
    projs=lims.get_projects(name=projname)
    jsondata=''
    try:
        proj=projs[0]
    except TypeError:
        print "No such project"
        raise TypeError
    else:

        data['projectid']=proj.id
        data['name']=proj.name
        data['pipeline']="NGI"
        data['sequencing_facility']="NGI-S"
        data['library_type']=proj.udf['Library construction method']
        data['best_practice_analysis']="IGN"
        if 'All samples sequenced' in proj.udf:
            data['status']='SEQUENCED'
        elif  'Samples received' in proj.udf:
            data['status']='OPEN'
        elif 'Sample information received' in proj.udf:
            data['status']='OPEN'
        else :
            data['status']='NEW' 

        data['samples']={}
        samples=lims.get_samples(projectlimsid=proj.id)    
        for sample in samples:
            sampinfo={ 'sampleid' : sample.name, 'received' : sample.date_received, "total_autosomal_coverage" : "0"}
            artf=lims.get_artifacts(process_type=INITIALQC.values(),sample_name=sample.name, qc_flag='FAILED')
            artp=lims.get_artifacts(process_type=INITIALQC.values(),sample_name=sample.name, qc_flag='PASSED')
            #if we have artifacts that say passed
            if len(artp)>0:
                sampinfo['lims_initial_qc']="Passed"

            for art in artf:
                #for each artifact that says failed
                if art.parent_process.type not in [a.parent_process.type for a in artp]:
                    #if the failed artifact process has been done again, and passed
                    # I am not checking dates on the assumption that we don't do again processes that pass qc 
                    sampinfo['lims_initial_qc']="Failed"
           #even when you want a process, it is easier to use getartifact, because you can filter by sample 
            libstart=lims.get_artifacts(process_type=PREPSTART.values(), sample_name=sample.name)
            #libstart=lims.get_processes(type=PREPSTART.values(), projectname=proj.name)
            libset=set()
            for art in libstart:
               libset.add(art.parent_process) 

            #Here I have all my lib preps start per sample in libs.

            libs=sorted(libset, key=lambda lib:lib.date_run)
 
            sampinfo['libs']={}
            #get pools
            seqarts=lims.get_artifacts(process_type=SEQSTART.values(), sample_name=sample.name, type='Analyte')

            alphaindex=65
            for lib in libs: 
                
                sampinfo['libs'][chr(alphaindex)]={}
                sampinfo['libs'][chr(alphaindex)]['libprepid']=chr(alphaindex)
                sampinfo['libs'][chr(alphaindex)]['status']="NEW"
                sampinfo['libs'][chr(alphaindex)]['limsid']=lib.id
                sampinfo['libs'][chr(alphaindex)]['seqruns']={}
                
                for sa in seqarts:
                    #get sequencing processes
                    seqevents=lims.get_processes(type=SEQUENCING.values(), projectname=proj.name,inputartifactlimsid=sa.id)
                    for se in seqevents:
                        if lib.id in procHistory(se, sample.name):
                            #if this sequencing happened after the given lib
                            #print se.id
                            if 'Run ID' in se.udf:
                                sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]={}
                                #short seqrunid is the first and last part of the run id concatenated with a _
                                sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['seqrunid']=se.udf['Run ID']
                                sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['mean_autosomal_coverage']=0
                                sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['sequencing_status']="DONE"
                                #the qc flag is on the input artifact of the sequencing run
                                sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['seq_qc_flag']=sa.qc_flag
                                sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['total_reads']=0
                                #get the artifacts generated by the demultiplexing (qc values are on them)
                                demarts=lims.get_artifacts(process_type=DEMULTIPLEX.values(), sample_name=sample.name)
                                for da in demarts:
                                    if da.qc_flag in ['PASSED', 'FAILED']:
                                        ph=procHistory(da.parent_process, sample.name)
                                        if sa.parent_process.id in ph:
                                            sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['demux_qc_flag']=da.qc_flag
                                            sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['total_reads']=da.udf['# Reads']
 


                alphaindex+=1
                #print "In sample {}".format(sample.name)
                #print "Seqrun {}".format(oneseqrun.id)
                #print "Libs {}".format([lib.id for lib in libs])
                #print oneseqrun.input_per_sample(sample.name)[0].id
                #print "History {}".format (h.history) 
                #print "====="
            data['samples'][sample.name]=sampinfo

    return data

def procHistory(proc, samplename):
    hist=[]
    processes=[]
    artifacts = lims.get_artifacts(sample_name = samplename, type = 'Analyte')
    not_done=True
    starting_art=proc.input_per_sample(samplename)[0].id
    while not_done:
        logging.info ("looking for ",(starting_art))
        not_done=False 
        for o in artifacts:
            logging.info (o.id)
            if o.id == starting_art:
                if o.parent_process is None:
                    #flow control : if there is no parent process, we can stop iterating, we're done.
                    not_done=False
                    break #breaks the for artifacts, we are done anyway.
                else:
                    not_done=True #keep the loop running
                logging.info ("found it")
                processes.append(o.parent_process)
                hist.append(o.parent_process.id)
                logging.info ("looking for inputs of "+o.parent_process.id)
                for i in o.parent_process.all_inputs():
                    logging.info (i.id)
                    if i in artifacts:
                        # while increment
                        starting_art=i.id
                            
                        break #break the for allinputs, if we found the right one
                break # breaks the for artifacts if we matched the current one
    return hist 

def cleanCharon(pname,options):
    session = requests.Session()
    headers = {'X-Charon-API-token': options.token, 'content-type': 'application/json'}
    projects=lims.get_projects(name = pname)
  
    r=session.delete(options.url+'/api/v1/project/'+projects[0].id, headers=headers)
    if options.verbose:
        if r.status_code==204:
            print "delete went ok"
        else:
            print r.status_code
            print r.reason

if __name__ == '__main__':
    usage = "Usage:       python acheron.py [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-t", "--token", dest="token", default=os.environ.get('CHARON_API_TOKEN'), 
            help="Charon API Token. Will be read from the env variable CHARON_API_TOKEN if not provided")
    parser.add_option("-u", "--url", dest="url", default=os.environ.get('CHARON_BASE_URL'), 
            help="Charon base url. Will be read from the env variable CHARON_BASE_URL if not provided")
    parser.add_option("-d", "--dummy", dest="dummy", default=False, action="store_true", 
            help="Will load the test project list and upload relevant data.")
    parser.add_option("-f", "--fake", dest="fake", default=False, action="store_true",
            help="don't actually do anything with the db, but print what will be uploaded")
    parser.add_option("-p", "--project", dest="proj", default=None, 
            help="-p <projectname> will try to upload the given project to charon")
    parser.add_option("-a", "--all", dest="all", default=False, action="store_true", 
            help="Try to upload all IGN projects. This will wipe the current information stored in Charon")
    parser.add_option("-n", "--new", dest="new", default=False, action="store_true", 
            help="Try to upload new IGN projects. This will NOT erase the current information stored in Charon")
    parser.add_option("-v", "--verbose", dest="verbose", default=False, action="store_true", 
            help="prints results for everything that is going on")
    (options, args) = parser.parse_args()
        
    if not options.token :
        print "No valid token found in arg or in environment. Exiting."
        sys.exit(-1)
    if not options.url:
        print "No valid url found in arg or in environment. Exiting."
        sys.exit(-1)

    main(options)
