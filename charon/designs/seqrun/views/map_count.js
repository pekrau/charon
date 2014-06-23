/* Charon
   Index libprep documents by [projectid, sampleid, libprepid].
   Value: number of seqruns.
*/
function(doc) {
    if (doc.charon_doctype !== 'libprep') return;
    emit([doc.projectid, doc.sampleid, doc.libprepid], doc.seqruns.length);
}
