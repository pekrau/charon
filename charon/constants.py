" Charon: Various constants."

import re

# For CouchDB view ranges.
# CouchDB uses the Unicode Collation Algorithm, which is not the same
# as the ASCII collation sequence. The endkey is inclusive, by default.
HIGH_CHAR = 'ZZZZZZZZ'

IUID_RX = re.compile(r'^[0-9a-z]{32}$')
ID_RX = re.compile(r'^[a-z][-._a-z0-9]*$', re.IGNORECASE)
RID_RX= re.compile(r'^[-._a-z0-9]*$', re.IGNORECASE)
ALLOWED_ID_CHARS= re.compile(r'[A-Za-z0-9\-\_]+', re.IGNORECASE)

# Tornado server
USER_COOKIE_NAME = 'charon_user'
TEMPLATE_PATH    = 'templates'
STATIC_PATH      = 'static'
STATIC_URL       = r'/static/'
LOGIN_URL        = r'/login'

# Database
DB_DOCTYPE = 'charon_doctype'
USER       = 'user'
PROJECT    = 'project'
SAMPLE     = 'sample'
LIBPREP    = 'libprep'
SEQRUN     = 'seqrun'
LOG        = 'log'

# Status
PENDING  = 'pending'
APPROVED = 'approved'
ACTIVE   = 'active'
BLOCKED  = 'blocked'
BASE_STATUS=['PASSED', 'FAILED']
ANALYSIS_STATUS=['TO_ANALYZE', 'UNDER_ANALYSIS', 'ANALYZED','INCOMPLETE', 'FAILED']
EXTENDED_STATUS=['NOT_RUNNING', 'RUNNING', 'DONE', 'FAILED']
GENO_STATUS=['AVAILABLE', 'NOT AVAILABLE', 'PASSED', 'FAILED']
PROJECT_STATUS=['OPEN', 'CLOSED', 'ABORTED']
SEQUENCING_STATUS=['NEW', 'SEQUENCED', 'IGNORED']

SEQ_FACILITIES=['NGI-S', 'NGI-U']
SAMPLE_TYPES=['NORMAL', 'CANCER']
