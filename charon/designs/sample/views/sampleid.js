/* Charon
   Index sample documents by [projectid, sampleid].
   Value: null.
*/
function(doc) {
    if (doc.charon_doctype !== 'sample') return;
    emit([doc.projectid, doc.sampleid], null);
}
