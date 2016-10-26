/*Returns all samples that have a 'not done' status*/

function(doc) {
        if (doc.charon_doctype === 'sample' && doc.status !== 'DONE'){ 
            emit([doc.projectid, doc.sampleid], doc);
        }
}
