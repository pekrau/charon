" Charon: Various constants."

import re

VERSION = '14.6'

HIGH_CHAR = unichr(2**16)

IUID_RX   = re.compile(r'^[0-9a-z]{32}$')

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
LOG        = 'log'

# Status
PENDING  = 'pending'
APPROVED = 'approved'
ACTIVE   = 'active'
BLOCKED  = 'blocked'
