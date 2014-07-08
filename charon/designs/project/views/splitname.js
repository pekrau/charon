/* Charon
   Index project documents by name split at first dot '.'.
   Value: projectid.
*/
function(doc) {
    if (doc.charon_doctype !== 'project') return;
    if (!doc.name) return;
    emit(doc.name, doc.projectid);
    var parts = doc.name.split(".", 2);
    if (parts.length < 2) return;
    emit(parts[1], doc.projectid);
}
