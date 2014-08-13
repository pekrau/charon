" Charon: Various constants."

import re

# For CouchDB view ranges.
# CouchDB uses the Unicode Collation Algorithm, which is not the same
# as the ASCII collation sequence. The endkey is inclusive, by default.
HIGH_CHAR = 'ZZZZZZZZ'

IUID_RX = re.compile(r'^[0-9a-z]{32}$')
ID_RX = re.compile(r'^[a-z][-._a-z0-9]*$', re.IGNORECASE)

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
BASE_STATUS=['NEW', 'RUNNING', 'DONE', 'FAILED']
EXTENDED_STATUS=['NEW', 'RUNNING', 'DONE', 'COMPUTATION_FAILED', 'DATA_FAILED']
GENO_STATUS=['ARRIVED', 'PROCESSED']
PROJECT_STATUS=['NEW', 'OPEN', 'CLOSED', 'ABORTED']


