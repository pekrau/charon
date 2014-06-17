/* Charon
   Index libprep documents by [projectid, sampleid].
   Value: 1.
*/
function(doc) {
    if (doc.charon_doctype !== 'libprep') return;
    emit([doc.projectid, doc.sampleid], 1);
}
