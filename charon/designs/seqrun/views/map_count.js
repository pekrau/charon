/* Charon
   Index seqrun documents by [projectid, sampleid, libprepid].
   Value: 1.
*/
function(doc) {
    if (doc.charon_doctype !== 'seqrun') return;
    emit([doc.projectid, doc.sampleid, doc.libprepid], 1);
}
