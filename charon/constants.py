" Charon: Various constants."

import re

HIGH_CHAR = unichr(2**8)        # Used for string range searches in CouchDB.

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
