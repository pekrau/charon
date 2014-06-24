/* Charon
   Index project documents by modified.
   Value: projectid.
*/
function(doc) {
    if (doc.charon_doctype !== 'project') return;
    if (!doc.modified) return;
    emit(doc.modified, doc.projectid);
}
