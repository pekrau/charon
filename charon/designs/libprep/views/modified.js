/* Charon
   Index libprep documents by modified.
   Value: [projectid, sampleid, libprepid].
*/
function(doc) {
    if (doc.charon_doctype !== 'libprep') return;
    if (!doc.modified) return;
    emit(doc.modified, [doc.projectid, doc.sampleid, doc.libprepid]);
}
