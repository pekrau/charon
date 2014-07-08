# Charon #

Database for IGN projects and samples, with RESTful interface.
Built on top of Tornado and CouchDB.


## API ##

The RESTful API is documented at http://charon-dev.scilifelab.se/apidoc .

A number of code examples for using the API can be found in the
nosetest `test_*.py` files.

Note that each call to the API must include an API token which is the
only mechanism used for authentication in the API. The API token is specific
for the user account, and is available in the user page for the account.


### Design notes ###

The API is designed such that all data sent to and received from the interface
is JSON containing pure application data. Metadata, such as the API access
token, is passed as a HTTP header item, so as not to clutter up the
data namespace. This also allows for sending other types of data as body
content, such as images, which cannot contain API access tokens.

Tip: Use the [requests](http://docs.python-requests.org/en/latest/)
package for all HTTP client code. It is way better than the urllib2 package
in the standard Python distribution.


## Development server ##

The development server is at http://charon-dev.scilifelab.se/ .
It is currently reachable only from within SciLifeLab Stockholm.

### Database wipe every weekend! ###

Please note that the CouchDB databases on tools-dev are all wiped clean
and reloaded from tools every weekend. Since there currently is no data
in the Charon database on tools, the tools-dev Charon instance gets
totally wiped out. Not even the design documents are spared.

To handle this, I currently manually dump and reload the Charon database,
on Friday afternoon and Monday morning, respectively:

    $ python dump.py

    $ python init_database.py # Answer 'y' to the question.

### Installation ###

The development server is installed as an ordinary Python package in
`/usr/lib/python2.6/site-packages/charon` . The controlling configuration
file `tools-dev.yaml` (which is not part of the GitHub stuff) is located there.
I have set the owner of that directory to `per.kraulis` to make it
simpler for me... 

The development server is upgraded thus:

    $ pip install --upgrade --no-deps git+https://github.com/NationalGenomicsInfrastructure/charon

The Tornado service is controlled by the upstart script `/etc/init/charon`.

The Apache server handles the redirect from the domain name to the Tornado
server which runs on port 8881. See `/etc/httpd/conf/httpd.conf`.

The log file written by the Tornado server currently goes to
the install directory.

## Production server ##

The production server has not yet been installed.
It will probably be at https://charon.scilifelab.se/ and will be reachable
from outside SciLifeLab to approved accounts.
