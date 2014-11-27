
from __future__ import print_function
import sys
import os
import codecs
from optparse import OptionParser
from pprint import pprint
from genologics.entities import *
from genologics.lims import *
from genologics.config import BASEURI, USERNAME, PASSWORD
from datetime import date
import yaml
import requests
import json
from types import *
import logging
import pdb
import datetime

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
DEMULTIPLEX={'13' : 'Bcl Conversion & Demultiplexing (Illumina SBS) 4.0'}

def main(options):
    if options.dummy:
        projs=['A.Wedell_13_03', 'G.Grigelioniene_14_01']
        for p in projs:
            data=prepareData(p)
            writeProjectData(data, options)
        addFakeData(options)
    if options.all:
        projs=findprojs('all')
        for pname, pid in projs:
            cleanCharon(pid, options)
            data=prepareData(pname)
            writeProjectData(data, options)
    elif options.new:
        projs=findprojs('all')
        for pname, pid in projs:
            newdata=prepareData(pname)
            olddata=getCompleteProject(newdata['projectid'], options)
            compareOldAndNew(olddata, newdata, options)

    elif options.proj:
        projs=findprojs(options.proj)
        for pname, pid in projs:
            cleanCharon(pid, options)
            data=prepareData(pname)
            writeProjectData(data, options)

    elif options.clean:
        session = requests.Session()
        headers = {'X-Charon-API-token': options.token, 'content-type': 'application/json'}
        rq=session.get('{0}/api/v1/projects'.format(options.url), headers=headers)
        projects=rq.json()
        projs=[p['projectid'] for p in projects['projects']]
        for p in projs:
            cleanCharon(p, options)
    elif options.delproj:
        cleanCharon(options.delproj, options)
    elif options.stress:
        stressTest(options)

        
def compareOldAndNew(old, new, options):
    autoupdate=False
    if old == None:
        writeProjectData(new, options)
        logging.info("updating {0}".format(new['projectid']))
    else:
        newsamples=new['samples']
        oldsamples=old['samples']
        if old['status']!=new['status']:
            old['status']=new['status']
            old.pop('samples')
            updateCharon(json.dumps(old), "{0}/api/v1/project/{1}".format(options.url, old['projectid']), options)

        for sampleid in newsamples:
            sample=newsamples[sampleid]
            libs=sample.pop('libs')

            if sampleid not in oldsamples:
                logging.info("updating {0}".format(sampleid))
                writeToCharon(json.dumps(sample),'{0}/api/v1/sample/{1}'.format(options.url, new['projectid']), options)
                autoupdate=True
                
            for libid in libs:
                lib=libs[libid]
                seqruns=lib.pop('seqruns')

                if autoupdate or libid not in oldsamples[sampleid]['libs']:  
                    print("updating {0} {1}".format(sampleid, libid))
                    writeToCharon(json.dumps(lib),'{0}/api/v1/libprep/{1}/{2}'.format(options.url, new['projectid'], sampleid), options)
                    autoupdate=True

                for seqrunid in seqruns:
                    seqrun=seqruns[seqrunid]
                    oldseqrun=oldsamples[sampleid]['libs'][libid]['seqruns'][seqrunid]
                    if autoupdate or seqrunid not in oldsamples[sampleid]['libs'][libid]['seqruns']:
                        logging.info("updating {0} {1} {2}".format(sampleid, libid, seqrunid))
                        writeToCharon(json.dumps(seqrun),'{0}/api/v1/seqrun/{1}/{2}/{3}'.format(options.url, new['projectid'], sampleid, libid), options)
                    elif(seqrun['lane_sequencing_status']!= oldseqrun['lane_sequencing_status']):
                        oldseqrun['lane_sequencing_status']=seqrun['lane_sequencing_status']
                        updateCharon(json.dumps(oldseqrun), '{0}/api/v1/seqrun/{1}/{2}/{3}/{4}'.format(options.url, new['projectid'], sampleid, libid, seqrunid), options)



def isDiff(dict1, dict2, var_keys):
    """returns true if dict1 and dict2 have different values in one of the var_keys, but the SAME values in all the other keys"""
    diff=False
    for key in dict1.keys():
        if key in var_keys and dict1.get(key) != dict2.get(key):
            diff=True
        if not key in var_keys and dict1.get(key) != dict2.get(key):
            return False
    return diff

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
        return [(p.name, p.id) for p in projects]
    else:
        projects=lims.get_projects(name=key)
        return [(p.name, p.id) for p in projects]

def updateCharon(jsonData, url, options):
    if options.fake:
        print( "data {0}".format(jsonData))
        print( "url {0}".format(url))
    else:
        session = requests.Session()
        headers = {'X-Charon-API-token': options.token, 'content-type': 'application/json'}
        r=session.put(url, headers=headers, data=jsonData)
        if options.verbose:
            logging.info(url)
            logging.info(jsonData)
            if r.status_code==201 or r.status_code==204:
                logging.info("update ok")
            elif r.status_code==400:
                logging.error("input data is wrong, {0}".format(r.reason))
            elif r.status_code==409:
                logging.error("Document is being updated")
            else:
                logging.error("Unknown error : {0} {0}".format(r.status_code, r.reason))
 
def writeToCharon(jsonData, url, options):
    if options.fake:
        print( "data {0}".format(jsonData))
        print( "url {0}".format(url))
    else:
        session = requests.Session()
        headers = {'X-Charon-API-token': options.token, 'content-type': 'application/json'}
        r=session.post(url, headers=headers, data=jsonData)
        if options.verbose:
            print( url)
            print( jsonData)
            if r.status_code in [201, 204]:
                print( "update ok")
            elif r.status_code==400:
                print( "input data is wrong, {0}".format(r.reason))
            elif r.status_code==409:
                print( "Document is being updated")
            else:
                print( "Unkown error : {0} {1}".format(r.status_code, r.text))
 
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
    data='{"sequencing_status": {1:"PASSED"}, "seqrunid": "130611_SN7001298_0148_AH0CCVADXX","mean_autosomal_coverage": 0, "total_reads": 693366930.0}'
    writeToCharon(data, url, options)
    data='{"sequencing_status": {1:"PASSED"}, "seqrunid": "130612_D00134_0019_AH056WADXX", "mean_autosomal_coverage": 0, "total_reads": 606139580.0}'
    writeToCharon(data, url,options )
    url=options.url+"/api/v1/seqrun/P567/P567_102/A"
    data='{"sequencing_status": {1:"PASSED"}, "seqrunid": "130627_D00134_0023_AH0JYUADXX",  "mean_autosomal_coverage": 0, "total_reads": 292171094.0}'
    writeToCharon(data, url, options)
    data='{"sequencing_status": {1:"PASSED"}, "seqrunid": "130701_SN7001298_0152_AH0J92ADXX",  "mean_autosomal_coverage": 0, "total_reads": 365307556.0}'
    writeToCharon(data, url, options)
    data='{"sequencing_status": {1:"PASSED"}, "seqrunid": "130701_SN7001298_0153_BH0JMGADXX",  "mean_autosomal_coverage": 0, "total_reads": 356267058.0}    '
    writeToCharon(data, url, options)


def prepareData(projname):

    data={}
    projs=lims.get_projects(name=projname)
    jsondata=''
    try:
        proj=projs[0]
    except TypeError:
        print( "No such project")
        raise TypeError
    else:

        data['projectid']=proj.id
        data['name']=proj.name
        data['pipeline']="NGI"
        data['sequencing_facility']="NGI-S"
        data['best_practice_analysis']="IGN"
        data['status']='OPEN'
        data['samples']={}
        samples=lims.get_samples(projectlimsid=proj.id)    
        for sample in samples:
            sampinfo={ 'sampleid' : sample.name, 'received' : sample.date_received, 'status' : 'NEW', 'total_autosomal_coverage' : "0"}
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
            seqevents=lims.get_processes(type=SEQUENCING.values(), projectname=proj.name)
            if seqevents:
                sampinfo['status']='NEW'
            alphaindex=65
            for lib in libs: 
                sampinfo['libs'][chr(alphaindex)]={}
                sampinfo['libs'][chr(alphaindex)]['libprepid']=chr(alphaindex)
                sampinfo['libs'][chr(alphaindex)]['limsid']=lib.id
                sampinfo['libs'][chr(alphaindex)]['seqruns']={}
                for se in seqevents:
                    if lib.id in procHistory(se, sample.name) and 'Run ID' in se.udf:
                        sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]={}
                        #short seqrunid is the first and last part of the run id concatenated with a _
                        sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['seqrunid']=se.udf['Run ID']
                        sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['mean_autosomal_coverage']=0
                        sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['total_reads']=0
                        sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['lane_sequencing_status']={}
                        for sa in se.all_inputs():
                            if sample.name in [s.name for s in sa.samples] and sa.type=="Analyte":
                                sampinfo['libs'][chr(alphaindex)]['seqruns'][se.udf['Run ID']]['lane_sequencing_status'][sa.location[1]]=sa.qc_flag
                                #get the artifacts generated by the demultiplexing (qc values are on them)

                alphaindex+=1
                #print( "In sample {0}".format(sample.name))
                #print( "Seqrun {0}".format(oneseqrun.id))
                #print( "Libs {0}".format([lib.id for lib in libs]))
                #print( oneseqrun.input_per_sample(sample.name)[0].id)
                #print( "History {0}".format (h.history) )
                #print( "=====")
            data['samples'][sample.name]=sampinfo

    return data

def procHistory(proc, samplename):
    hist=[]
    processes=[]
    artifacts = lims.get_artifacts(sample_name = samplename, type = 'Analyte')
    not_done=True
    try:
        starting_art=proc.input_per_sample(samplename)[0].id
    except:
        return []
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

def stressTest(options):
    testprojects=[]
    print( "#"*10)
    print( "Start : {0}".format(datetime.datetime.now().isoformat()))
    print( "#"*10)
    for n in xrange(1,options.stress+1):
    #    d=genFakeFroject(n, 'TEST_{0}'.format(n),200, 1, 1)
    #    writeProjectData(d, options)
        testprojects.append('TEST_{0}'.format(n))

    print( "#"*10)
    print( "{0} :Done uploading. Querying...".format(datetime.datetime.now().isoformat()))
    print( "#"*10)
    i=0
    for p in testprojects:
        i+=1
        if (i%100==0):
            print(("\n"))
        try:
            getCompleteProject(p, options)
            print(".", end='')
        except requests.exceptions.ConnectionError as e:
            print ("\nF {0} : {1}".format(p, e))

    print( "#"*10)
    print( "{0} : Queries are done. Deleting ...".format(datetime.datetime.now().isoformat()))
    print( "#"*10)
    for p in testprojects:
        cleanCharon(p, options)


def genFakeFroject(number,name,samplesnb, libsnb, seqrunsnb):
    data={}
    data['projectid']='TEST_{0}'.format(number)
    data['name']=name
    data['pipeline']="TEST"
    data['sequencing_facility']="NGI-S"
    data['best_practice_analysis']="TEST"
    data['status']='CLOSED' 
    data['samples']={}
    for s in xrange(1,samplesnb+1):
        sampinfo={ 'sampleid' : "TEST_{0}_{1}".format(number,s), 'received' : datetime.datetime.today().strftime("%Y-%m-%d"), "total_autosomal_coverage" : "0", "libs":{}}
        alphaindex=65
        for l in xrange(1,libsnb+1):
            sampinfo['libs'][chr(alphaindex)]={}
            sampinfo['libs'][chr(alphaindex)]['libprepid']=chr(alphaindex)
            sampinfo['libs'][chr(alphaindex)]['seqruns']={}
            for r in xrange(1, seqrunsnb+1):
                sampinfo['libs'][chr(alphaindex)]['seqruns']["TESTFC_{0}_{1}_{2}_{3}".format(number,s,chr(alphaindex),r)]={}
                sampinfo['libs'][chr(alphaindex)]['seqruns']["TESTFC_{0}_{1}_{2}_{3}".format(number,s,chr(alphaindex),r)]['seqrunid']="TESTFC_{0}_{1}_{2}_{3}".format(number,s,chr(alphaindex), r)
                sampinfo['libs'][chr(alphaindex)]['seqruns']["TESTFC_{0}_{1}_{2}_{3}".format(number,s,chr(alphaindex),r)]['mean_autosomal_coverage']=0
                sampinfo['libs'][chr(alphaindex)]['seqruns']["TESTFC_{0}_{1}_{2}_{3}".format(number,s,chr(alphaindex),r)]['sequencing_status']={1:"DONE"}
                #the qc flag is on the input artifact of the sequencing run
                sampinfo['libs'][chr(alphaindex)]['seqruns']["TESTFC_{0}_{1}_{2}_{3}".format(number,s,chr(alphaindex),r)]['total_reads']=0

            alphaindex+=1
        data['samples']["TEST_{0}_{1}".format(number,s)]=sampinfo
        
        
    return(data)
    



def cleanCharon(pid,options):
    if options.verbose:
        logging.info("removing project {0}".format(pid))
    session = requests.Session()
    headers = {'X-Charon-API-token': options.token, 'content-type': 'application/json'}
  
    r=session.delete(options.url+'/api/v1/project/'+pid, headers=headers)
    if options.verbose:
        if r.status_code==204:
            logging.info("delete went ok")
        else:
            logging.error(r.status_code)
            logging.error(r.reason)

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
    parser.add_option("-r", "--remove", dest="delproj", default=None, 
            help="-r <projectname> will try to remove the given project to charon")
    parser.add_option("-a", "--all", dest="all", default=False, action="store_true", 
            help="Try to upload all IGN projects. This will wipe the current information stored in Charon")
    parser.add_option("-n", "--new", dest="new", default=False, action="store_true", 
            help="Try to upload new IGN projects. This will NOT erase the current information stored in Charon")
    parser.add_option("-c", "--clean", dest="clean", default=False, action="store_true", 
            help="This will erase the current information stored in Charon")
    parser.add_option("-v", "--verbose", dest="verbose", default=False, action="store_true", 
            help="prints results for everything that is going on")
    parser.add_option("-s", "--stress", type="int",dest="stress", default=0,
            help="-s N : stresses charon with N projects")
    (options, args) = parser.parse_args()
        
    if not options.token :
        print( "No valid token found in arg or in environment. Exiting.")
        sys.exit(-1)
    if not options.url:
        print( "No valid url found in arg or in environment. Exiting.")
        sys.exit(-1)

    main(options)
