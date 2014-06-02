/* Charon
   Index project documents by projectid.
   Value: projectname, or null.
*/
function(doc) {
    if (doc.charon_doctype !== 'project') return;
    emit(doc.projectid, doc.projectname || null);
}
