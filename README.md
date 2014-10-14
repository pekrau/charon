# Charon #

Database for IGN projects and samples, with RESTful interface.
Built on top of Tornado and CouchDB.


## API ##

The RESTful API is documented at http://charon.scilifelab.se/apidoc .

Note that each call to the API must include an API token which is the
only mechanism used for authentication in the API. The API token is specific
for the user account, and is available in the user page for the account.

A number of code examples for using the API can be found in the
nosetest `test_*.py` files.

The nosetest examples require that the environment variables
CHARON_API_TOKEN and CHARON_BASE_URL are set.


### Design notes ###

The API is designed such that all data sent to and received from the interface
is JSON containing pure application data. Metadata, such as the API access
token, is passed as a HTTP header item, so as not to clutter up the
data namespace. This also allows for sending other types of data as body
content, such as images, which cannot contain API access tokens.

**Tip**: Use the [requests](http://docs.python-requests.org/en/latest/)
package for all HTTP client code. It is way better than the urllib2 package
in the standard Python distribution.


## Development server ##

The development server is at http://charon-dev.scilifelab.se/ .
It is currently reachable only from within SciLifeLab Stockholm.

Charon-dev is deployed as Hiseq boinfo, in an anaconda virtual anvironment named "charon_env"
The logfile is located within the repo (~/opt/charon/charon/charon.log)

To update Charon, move to the repo and execute "git pull". If the modifications are not 
automatically reloaded by Tornado (a change in the configuration files, for instance)
kill the current charon process, and start it again. 

Note that the working directory needs to be the one containing "app_charon.py".
The configuration file "tools-dev.yaml" is located there as well. It's not saved on github.

We should be getting an upstart configuration to do that properly soon.

### Couchdb Replication ###

The tables from the production couchdb server are replicated dailyto the dev server.
This should have been deactivated for Charon, but if that is switched on again for
whatever reason, Charon-dev WILL fail, since we will get more than one document with the same key.

### Backup plan ###
On a daily basis, the content of couchdb is dumped to the disk. If something goes wrong,
it is possible to reinitialise the database with the dumps.
>dump.py
    dumps the current state of the database into dump.tar.gz
>python init_database.py 
    tries to upload the dump.tar.gz to the database

### Other notes ###

The Apache server handles the redirect from the domain name to the Tornado
server which runs on port 8881. See `/etc/httpd/conf/httpd.conf`.

## Production server ##

The production server is available at http://charon.scilifelab.se/ and is
reachable from outside SciLifeLab to approved accounts, which are set up
using Userman at http://userman.scilifelab.se/ .

The production server is upgraded in a similar way as the development server.

### Service setup ###

The source code used in production is located in:

    ~/anaconda/envs/charon_env/lib/python2.6/site-packages/charon

The configuration file tools.yaml is located in:

    ~/opt/charon/charon

The log file charon.log is located in:

    ~/opt/charon/charon

This is due to the fact that hiseq.bioinfo does not belong to a froup allowed to write in /var/log
The production server is upgraded thus:

    $ source ~/anaconda/bin/activate charon_env
    $ cd ~/opt/charon;git pull; python setup.py install

The production server is currently started manually by hiseq.bioinfo 

    $ source ~/anaconda/bin/activate charon_env
    $ cd ~/opt/charon/charon
    $ python app_charon.py tools.yaml


