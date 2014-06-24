/* Charon
   Index sample documents by modified.
   Value: [projectid, sampleid].
*/
function(doc) {
    if (doc.charon_doctype !== 'sample') return;
    if (!doc.modified) return;
    emit(doc.modified, [doc.projectid, doc.sampleid]);
}
