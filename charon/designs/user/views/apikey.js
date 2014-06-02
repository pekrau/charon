/* Charon
   Index user documents by API key.
   Value: email.
*/
function(doc) {
    if (doc.charon_doctype !== 'user') return;
    emit(doc.apikey, doc.email);
}
