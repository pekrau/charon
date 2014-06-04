" Charon: Database for IGN projects and samples, with RESTful interface. "

import socket
import yaml

import constants
__version__ = constants.VERSION


settings = dict(HOSTNAME=socket.gethostname().split('.')[0],
                TORNADO_DEBUG=True,
                LOGGING_DEBUG=False,
                URL_PORT=8881,
                BASE_URL='http://localhost:8881/',
                DB_SERVER='http://localhost:5984/',
                DB_DATABASE='charon',
                )

with open("{0}.yaml".format(settings['HOSTNAME'])) as infile:
    settings.update(yaml.safe_load(infile))
