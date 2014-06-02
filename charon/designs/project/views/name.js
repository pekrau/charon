/* Charon
   Index project documents by name.
   Value: projectid.
*/
function(doc) {
    if (doc.charon_doctype !== 'project') return;
    if (!doc.name) return;
    emit(doc.name, doc.projectid);
}
