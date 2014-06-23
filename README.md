Charon
======

Database for IGN projects and samples, with RESTful interface.
Built on top of Tornado and CouchDB.

API
---

The RESTful API is documented at http://charon-dev.scilifelab.se/apidoc .

A number of code examples for using the API can be found in the
nosetest **test_*.py** files.

Note that each call to the API must include an API token which is the
only mechanism used for authentication in the API. The API token is specific
for the user account, and is available in the user page for the account.

Development server
------------------

The development server is at http://charon-dev.scilifelab.se/ .
It is currently reachable only from within SciLifeLab Stockholm.

Production server
-----------------

The production server has not yet been installed.
It will probably be at https://charon.scilifelab.se/ and will be reachable
from outside SciLifeLab to approved accounts.
