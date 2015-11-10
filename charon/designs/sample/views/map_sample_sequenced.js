function(doc) {
  if (doc.charon_doctype === 'seqrun'){
	 emit([doc.projectid, doc.sampleid], 1);
  }
}