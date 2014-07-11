""" Charon: Initialize the database, working directly towards CouchDB.

1) Wipeout the old database.
2) Load the design documents.
3) Load the dump file, if any.
"""

import os

from charon import constants
from charon import utils
from charon.load_designs import load_designs
from charon.dump import undump


def wipeout_database(db):
    "Wipe out the contents of the database."
    for doc in db:
        del db[doc]


if __name__ == '__main__':
    import sys

    # import argparse
    # parser = argparse.ArgumentParser(description='Initialize and load Charon database from dump file')
    # parser.add_argument('--force', action='store_true',
    #                     help='force action, rather than ask for confirmation')
    # parser.add_argument('filepath', type=str, nargs='?', default=None,
    #                     help='filepath for YAML settings file')
    # args = parser.parse_args()

    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-f", "--force",
                      action="store_true", dest="force", default=True,
                      help='force action, rather than ask for confirmation')
    (options, args) = parser.parse_args()

    if not options.force:
        response = raw_input('about to delete everything; really sure? [n] > ')
        if not utils.to_bool(response):
            sys.exit('aborted')
    if len(args) == 0:
        filepath = None
    elif len(args) == 1:
        filepath = args[0]
    else:
        sys.exit('too many arguments')
    utils.load_settings(filepath=filepath)

    db = utils.get_db()
    wipeout_database(db)
    print 'wiped out database'
    load_designs(db)
    print 'loaded designs'
    default = 'dump.tar.gz'
    if options.force:
        filename = default
    else:
        filename = raw_input("load data from file? [{0}] > ".format(default))
        if not filename:
            filename = default
    if os.path.exists(filename):
        count_items, count_files = undump(db, filename)
        print 'undumped', count_items, 'items and', count_files, 'files from', filename
    else:
        print 'no such file to undump'
