/* Charon
   Index sample documents by projectid.
   Value: 1.
*/
function(doc) {
    if (doc.charon_doctype === 'sample' && doc.status === "DONE") emit(doc.projectid, 1);
}
