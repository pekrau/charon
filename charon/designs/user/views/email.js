/* Charon
   Index user documents by email.
   Value: null.
*/
function(doc) {
    if (doc.charon_doctype !== 'user') return;
    emit(doc.email, null);
}
