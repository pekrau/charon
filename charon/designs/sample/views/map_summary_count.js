/* Charon
 *    summaries for all the samples and per project.
 *       Value: 1.
 *       */
function(doc) {
    seq_sa=[];
    if (doc.charon_doctype === 'sample'){
        emit('TOTAL', 1);
        emit(doc.projectid+'_TOTAL', 1);
        emit('TOTAL_COV', doc.total_autosomal_coverage);
        emit(doc.projectid+'_TOTAL_COV', doc.total_autosomal_coverage);
        if (doc.analysis_status === 'ANALYZED'){
            emit('ANALYZED', 1);
            emit(doc.projectid+'_ANALYZED', 1);
        }
        else if (doc.analysis_status === 'UNDER_ANALYSIS'){
        emit('UNDER_ANALYSIS', 1);
        emit(doc.projectid+'_UNDER_ANALYSIS', 1);
        }
        else if (doc.analysis_status === 'FAILED'){
        emit('FAILED', 1);
        emit(doc.projectid+'_FAILED', 1);
        }
    }else if (doc.charon_doctype === 'seqrun'){
        if (seq_sa.indexOf(doc.sampleid) == -1){
        seq_sa.push(doc.sampleid);
        emit('SEQUENCED', 1);
        emit(doc.projectid+'_SEQUENCED', 1);
        }
    }
}
