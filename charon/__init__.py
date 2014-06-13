" Charon: Database for IGN projects and samples, with RESTful interface. "

__version__ = '14.6'

settings = dict(BASE_URL='http://localhost:8881/',
                DB_SERVER='http://localhost:5984/',
                DB_DATABASE='charon',
                TORNADO_DEBUG=True,
                LOGGING_DEBUG=True,
                )
