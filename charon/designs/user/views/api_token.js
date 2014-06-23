/* Charon
   Index user documents by API token.
   Value: email.
*/
function(doc) {
    if (doc.charon_doctype !== 'user') return;
    emit(doc.api_token, doc.email);
}
