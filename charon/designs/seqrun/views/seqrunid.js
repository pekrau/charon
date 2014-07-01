/* Charon
   Index seqrun documents by [projectid, sampleid, libprepid, seqrunid].
   Value: null.
*/
function(doc) {
    if (doc.charon_doctype !== 'seqrun') return;
    emit([doc.projectid, doc.sampleid, doc.libprepid, doc.seqrunid], null);
}
