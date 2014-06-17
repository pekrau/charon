""" Charon: Initialize the database.

1) Wipeout the old database.
2) Load the design documents.
3) Load the dump file, if any.
"""

import os
import getpass

from charon import settings
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
    response = raw_input('about to delete everything; really sure? [n] > ')
    try:
        utils.load_settings(filepath=sys.argv[1])
    except IndexError:
        utils.load_settings()
    if utils.to_bool(response):
        db = utils.get_db()
        wipeout_database(db)
        print 'wiped out database'
        load_designs(db)
        print 'loaded designs'
        default = 'dump.tar.gz'
        filename = raw_input("load data from file? [{0}] > ".format(default))
        if not filename:
            filename = default
        if os.path.exists(filename):
            count_items, count_files = undump(db, filename)
            print 'undumped', count_items, 'items and', count_files, 'files from', filename
        else:
            print 'no such file to undump'
