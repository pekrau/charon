/* Charon
   Index user documents by name and parts of the name.
   Value: email.
*/
function(doc) {
    if (doc.charon_doctype !== 'user') return;
    if (!doc.name) return;
    emit(doc.name, doc.email);
    var parts = doc.name.split(" ");
    if (parts.length > 1) {
	for (var i=0; i<parts.length; i++) {
	    emit(parts[i], doc.email);
	};
    };
}
