/*emits only not done projects*/
function(doc) {
    if (doc.charon_doctype === 'project' && doc.status !== 'CLOSED'){
          emit(doc.projectid, doc);
    }
}
