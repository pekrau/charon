
import argparse
import json
import logging
import multiprocessing as mp
import Queue
import requests
import time

from datetime import datetime
from genologics_sql.tables import *
from genologics_sql.utils import *
from genologics_sql.queries import *
from sqlalchemy import text
from charon.utils import QueueHandler

VALID_BIOINFO_QC=['WG re-seq (IGN)','WG re-seq', 'RNA-seq']

def main(args):
    main_log=setup_logging("acheron_logger", args)
    docs=[]
    db_session=get_session()
    if args.proj:
        main_log.info("Updating {0}".format(args.proj))
        docs=generate_data(args.proj, db_session)
        update_charon(docs, args, main_log)
    elif args.new:
        project_list=obtain_recent_projects(db_session)
        main_log.info("Project list : {0}".format(", ".join([x.luid for x in project_list])))
        masterProcess(args, project_list, main_log)
    elif args.all:
        project_list=obtain_valid_projects(db_session)
        main_log.info("Project list : {0}".format(", ".join([x.luid for x in project_list])))
        masterProcess(args, project_list, main_log)
    elif args.test:
        print "\n".join(x.__str__() for x in obtain_recent_projects(db_session))
        print "##########"
        print "\n".join(x.__str__() for x in obtain_valid_projects(db_session))

def setup_logging(name, args):
    mainlog = logging.getLogger(name)
    mainlog.setLevel(level=logging.INFO)
    mfh = logging.handlers.RotatingFileHandler(args.logfile, maxBytes=209715200, backupCount=5)
    mft = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    mfh.setFormatter(mft)
    mainlog.addHandler(mfh)
    return mainlog

def obtain_valid_projects(session):
    query="select pj.* from project pj \
            inner join entity_udf_view euv on pj.projectid=euv.attachtoid \
            where euv.attachtoclassid=83 and \
            euv.udfname like 'Bioinformatic QC' and \
            euv.udfvalue in ({0}) and \
            pj.createddate > date '2016-01-01';".format(",".join(["'{0}'".format(x) for x in VALID_BIOINFO_QC]))
    return session.query(Project).from_statement(text(query)).all()

def obtain_recent_projects(session):
    recent_projectids=get_last_modified_projectids(session)
    if recent_projectids:
        query="select pj.* from project pj \
            inner join entity_udf_view euv on pj.projectid=euv.attachtoid \
            where euv.attachtoclassid=83 and \
            euv.udfname like 'Bioinformatic QC' and \
            euv.udfvalue in ({0}) and \
            pj.luid in ({1});".format(",".join(["'{0}'".format(x) for x in VALID_BIOINFO_QC]), ",".join(["'{0}'".format(x) for x in recent_projectids]))
        return session.query(Project).from_statement(text(query)).all()
    else:
        return []

def generate_data(project_id, session):
    docs=[]
    project=obtain_project(project_id, session)
    docs.append(generate_project_doc(project))
    docs.extend(generate_samples_docs(project))
    docs.extend(generate_libprep_seqrun_docs(project, session))
    return docs

def obtain_project(project_id, session):
    query="select pj.* from project pj \
            where pj.luid LIKE '{pid}'::text OR pj.name LIKE '{pid}';".format(pid=project_id)
    return session.query(Project).from_statement(text(query)).one()

def generate_project_doc(project):
    curtime=datetime.now().isoformat()
    doc={}
    doc['charon_doctype']='project'
    doc['created']=curtime
    doc['modified']=curtime
    doc['sequencing_facility']='NGI-S'
    doc['pipeline']='NGI'
    doc['projectid']=project.luid
    doc['status']='OPEN'

    doc['name']=project.name
    for udf in project.udfs:
        if udf.udfname=='Bioinformatic QC':
            if udf.udfvalue == 'WG re-seq':
                doc['best_practice_analysis']='whole_genome_reseq'
            else:
                doc['best_practice_analysis']=udf.udfvalue
        if udf.udfname=='Uppnex ID' and udf.udfvalue:
            doc['uppnex_id']=udf.udfvalue.strip()


    return doc

def generate_samples_docs(project):
    curtime=datetime.now().isoformat()
    docs=[]
    for sample in project.samples:
        doc={}
        doc['charon_doctype']='sample'
        doc['projectid']=project.luid
        doc['sampleid']=sample.name
        doc['created']=curtime
        doc['modified']=curtime
        doc['duplication_pc']=0
        doc['genotype_concordance']=0
        doc['total_autosomal_coverage']=0
        doc['status']='NEW'
        doc['analysis_status']='TO_ANALYZE'
        for udf in sample.udfs:
            if udf.udfname=='Reads Req':
                doc['requested_reads']=udf.udfvalue
            if udf.udfname=='Status (Manual)':
                if udf.udfvalue == 'Aborted':
                    doc['status']='ABORTED'

        docs.append(doc)

    return docs

def generate_libprep_seqrun_docs(project, session):
    curtime=datetime.now().isoformat()
    docs=[]
    for sample in project.samples:
        query="select pc.* from process pc \
        inner join processiotracker piot on piot.processid=pc.processid \
        inner join artifact_sample_map asm on asm.artifactid=piot.inputartifactid \
        where asm.processid={pcid} and pc.typeid in (8,806);".format(pcid=sample.processid)
        libs=session.query(Process).from_statement(text(query)).all()
        alphaindex=65
        for lib in libs:
            doc={}
            doc['charon_doctype']='libprep'
            doc['created']=curtime
            doc['modified']=curtime
            doc['projectid']=project.luid
            doc['sampleid']=sample.name
            doc['libprepid']=chr(alphaindex)
            doc['qc']="PASSED"
            docs.append(doc)
            query="select distinct pro.* from process pro \
            inner join processiotracker pio on pio.processid=pro.processid \
            inner join artifact_sample_map asm on pio.inputartifactid=asm.artifactid \
            inner join artifact_ancestor_map aam on pio.inputartifactid=aam.artifactid\
            inner join processiotracker pio2 on pio2.inputartifactid=aam.ancestorartifactid\
            inner join process pro2 on pro2.processid=pio2.processid \
            where pro2.processid={parent} and pro.typeid in (38,46,714) and asm.processid={sid};".format(parent=lib.processid, sid=sample.processid)
            seqs=session.query(Process).from_statement(text(query)).all()
            for seq in seqs:
                seqdoc={}
                seqdoc['charon_doctype']='seqrun'
                seqdoc['created']=curtime
                seqdoc['modified']=curtime
                seqdoc['mean_autosomal_coverage']=0
                seqdoc['total_reads']=0
                seqdoc['alignment_status']='NOT_RUNNING'
                seqdoc['delivery_status']='NOT_DELIVERED'
                seqdoc['projectid']=project.luid
                seqdoc['sampleid']=sample.name
                seqdoc['libprepid']=chr(alphaindex)
                for udf in seq.udfs:
                    if udf.udfname=="Run ID":
                        seqdoc['seqrunid']=udf.udfvalue
                        break
                if 'seqrunid' in seqdoc:
                    docs.append(seqdoc)


            alphaindex+=1

    return docs

def update_charon(docs, args, logger):
    session=requests.Session()
    headers = {'X-Charon-API-token': args.token, 'content-type': 'application/json'}
    for doc in docs:
        if doc['charon_doctype']=='project':
            logger.info("trying to update doc {0}".format(doc['projectid']))
            url="{0}/api/v1/project/{1}".format(args.url, doc['projectid'])
            r=session.get(url, headers=headers)
            if r.status_code==404:
                url="{0}/api/v1/project".format(args.url)
                rq=session.post(url, headers=headers, data=json.dumps(doc))
                if rq.status_code == requests.codes.created:
                    logger.info("project {0} successfully updated".format(doc['projectid']))
                else:
                    logger.error("project {0} failed to be updated : {1}".format(doc['projectid'], rq.text))
            else:
                pj=r.json()
                merged=merge(pj, doc)
                rq=session.put(url, headers=headers, data=json.dumps(merged))
                if rq.status_code == requests.codes.no_content:
                    logger.info("project {0} successfully updated".format(doc['projectid']))
                else:
                    logger.error("project {0} failed to be updated : {1}".format(doc['projectid'], rq.text))
        elif doc['charon_doctype']=='sample':
            url="{0}/api/v1/sample/{1}/{2}".format(args.url, doc['projectid'], doc['sampleid'])
            r=session.get(url, headers=headers)
            if r.status_code==404:
                url="{0}/api/v1/sample/{1}".format(args.url, doc['projectid']) 
                rq=session.post(url, headers=headers, data=json.dumps(doc))
                if rq.status_code == requests.codes.created:
                    logger.info("sample {0}/{1} successfully updated".format(doc['projectid'], doc['sampleid']))
                else:
                    logger.error("sample {0}/{1} failed to be updated : {2}".format(doc['projectid'], doc['sampleid'], rq.text))
            else:
                pj=r.json()
                merged=merge(pj, doc)
                rq=session.put(url, headers=headers, data=json.dumps(merged))
                if rq.status_code == requests.codes.no_content:
                    logger.info("sample {0}/{1} successfully updated".format(doc['projectid'], doc['sampleid']))
                else:
                    logger.error("sample {0}/{1} failed to be updated : {2}".format(doc['projectid'], doc['sampleid'], rq.text))
        elif doc['charon_doctype']=='libprep':
            url="{0}/api/v1/libprep/{1}/{2}/{3}".format(args.url, doc['projectid'], doc['sampleid'], doc['libprepid'])
            r=session.get(url, headers=headers)
            if r.status_code==404:
                url="{0}/api/v1/libprep/{1}/{2}".format(args.url, doc['projectid'], doc['sampleid']) 
                rq=session.post(url, headers=headers, data=json.dumps(doc))
                if rq.status_code == requests.codes.created:
                    logger.info("libprep {0}/{1}/{2} successfully updated".format(doc['projectid'], doc['sampleid'], doc['libprepid']))
                else:
                    logger.error("libprep {0}/{1}/{2} failed to be updated : {3}".format(doc['projectid'], doc['sampleid'], doc['libprepid'], rq.text))
            else:
                pj=r.json()
                merged=merge(pj, doc)
                rq=session.put(url, headers=headers, data=json.dumps(merged))
                if rq.status_code == requests.codes.no_content:
                    logger.info("libprep {0}/{1}/{2} successfully updated".format(doc['projectid'], doc['sampleid'], doc['libprepid']))
                else:
                    logger.error("libprep {0}/{1}/{2} failed to be updated : {3}".format(doc['projectid'], doc['sampleid'], doc['libprepid'], rq.text))
        elif doc['charon_doctype']=='seqrun':
            url="{0}/api/v1/seqrun/{1}/{2}/{3}/{4}".format(args.url, doc['projectid'], doc['sampleid'], doc['libprepid'], doc['seqrunid'])
            r=session.get(url, headers=headers)
            if r.status_code==404:
                url="{0}/api/v1/seqrun/{1}/{2}/{3}".format(args.url, doc['projectid'], doc['sampleid'], doc['libprepid']) 
                rq=session.post(url, headers=headers, data=json.dumps(doc))
                if rq.status_code == requests.codes.created:
                    logger.info("seqrun {0}/{1}/{2}/{3} successfully updated".format(doc['projectid'], doc['sampleid'], doc['libprepid'], doc['seqrunid']))
                else:
                    logger.error("seqrun {0}/{1}/{2}/{3} failed to be updated : {4}".format(doc['projectid'], doc['sampleid'], doc['libprepid'], doc['seqrunid'], rq.text))
            else:
                pj=r.json()
                merged=merge(pj, doc)
                rq=session.put(url, headers=headers, data=json.dumps(merged))
                if rq.status_code == requests.codes.no_content:
                    logger.info("seqrun {0}/{1}/{2}/{3} successfully updated".format(doc['projectid'], doc['sampleid'], doc['libprepid'], doc['seqrunid']))
                else:
                    logger.error("seqrun {0}/{1}/{2}/{3} failed to be updated : {4}".format(doc['projectid'], doc['sampleid'], doc['libprepid'], doc['seqrunid'], rq.text))

def merge(d1, d2):
    """ Will merge dictionary d2 into dictionary d1.
    On the case of finding the same key, the one in d1 will be used.
    :param d1: Dictionary object
    :param s2: Dictionary object
    """
    for key in d2:
        if key in d1:
            if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                merge(d1[key], d2[key])
            elif d1[key] == d2[key]:
                pass # same leaf value
        else:
            d1[key] = d2[key]
    return d1

def masterProcess(args, projectList, logger):
    projectsQueue=mp.JoinableQueue()
    logQueue=mp.Queue()
    childs=[]
    #spawn a pool of processes, and pass them queue instance 
    for i in range(args.processes):
        p = mp.Process(target=processCharon, args=(args, projectsQueue, logQueue))
        p.start()
        childs.append(p)
    #populate queue with data   
    for proj in projectList:
        projectsQueue.put(proj.luid)

    #wait on the queue until everything has been processed     
    notDone=True
    while notDone:
        try:
            log=logQueue.get(False)
            logger.handle(log)
        except Queue.Empty:
            if not stillRunning(childs):
                notDone=False
                break

def stillRunning(processList):
    ret=False
    for p in processList:
        if p.is_alive():
            ret=True

    return ret

def processCharon(args, queue, logqueue):
    session=get_session()
    work=True
    procName=mp.current_process().name
    proclog=logging.getLogger(procName)
    proclog.setLevel(level=logging.INFO)
    mfh = QueueHandler(logqueue)
    mft = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    mfh.setFormatter(mft)
    proclog.addHandler(mfh)
    try:
        time.sleep(int(procname[8:]))
    except:
        time.sleep(1)

    while work:
        #grabs project from queue
        try:
            proj_id= queue.get(block=True, timeout=3)
        except Queue.Empty:
            work=False
            break
        except NotImplementedError:
            #qsize failed, no big deal
            pass
        else:
            #locks the project : cannot be updated more than once.
            proclog.info("Handling {}".format(proj_id))
            docs=generate_data(proj_id, session)
            update_charon(docs, args, proclog)

            #signals to queue job is done
            queue.task_done()

if __name__=="__main__":
    usage = "Usage:       python acheron_sql.py [options]"
    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument("-k", "--processes", dest="processes", default=12, type=int, 
            help="Number of child processes to start")
    parser.add_argument("-a", "--all", dest="all", default=False, action="store_true", 
            help="Try to upload all IGN projects. This will wipe the current information stored in Charon")
    parser.add_argument("-n", "--new", dest="new", default=False, action="store_true", 
            help="Try to upload new IGN projects. This will NOT erase the current information stored in Charon")
    parser.add_argument("-p", "--project", dest="proj", default=None, 
            help="-p <projectname> will try to upload the given project to charon")
    parser.add_argument("-t", "--token", dest="token", default=os.environ.get('CHARON_API_TOKEN'), 
            help="Charon API Token. Will be read from the env variable CHARON_API_TOKEN if not provided")
    parser.add_argument("-u", "--url", dest="url", default=os.environ.get('CHARON_BASE_URL'), 
            help="Charon base url. Will be read from the env variable CHARON_BASE_URL if not provided")
    parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true", 
            help="prints results for everything that is going on")
    parser.add_argument("-l", "--log", dest="logfile", default=os.path.expanduser("~/acheron.log"), 
            help="location of the log file")
    parser.add_argument("-z", "--test", dest="test", default=False, action="store_true", 
            help="Testing option")
    args = parser.parse_args()
        
    if not args.token :
        print( "No valid token found in arg or in environment. Exiting.")
    if not args.url:
        print( "No valid url found in arg or in environment. Exiting.")
        sys.exit(-1)
    main(args)
