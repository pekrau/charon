"Test speed of CouchDB connection."

import os
import time
import uuid

import couchdb


def do_create(db, total=400):
    timer = Timer()
    count = 0
    for i in xrange(total):
        doc = dict(id=uuid.uuid4().hex,
                   number=i,
                   doctype='garbage')
        db.save(doc)
        count += 1
    print 'create', count, timer

def do_read(db):
    timer = Timer()
    count = 0
    for key in db:
        doc = db[key]
        # print doc.id
        count += 1
    print 'read', count, timer

def do_delete(db):
    timer = Timer()
    count = 0
    for key in list(db):
        doc = db[key]
        try:
            if doc['doctype'] == 'garbage':
                del db[key]
                count += 1
        except KeyError:
            pass
    print 'delete', count, timer


class Timer(object):

    def __init__(self):
        self.start_cpu = time.clock()
        self.start_wall = time.time()

    def __str__(self):
        return "[%.2f, %s]" % (self.wall, self.cpu)

    @property
    def cpu(self):
        return time.clock() - self.start_cpu

    @property
    def wall(self):
        return time.time() - self.start_wall


if __name__ == '__main__':
    import sys
    COUCHDB_SERVER = sys.argv[1]
    COUCHDB_DATABASE = 'charon'
    server = couchdb.Server(COUCHDB_SERVER)
    print server.version()
    db = server[COUCHDB_DATABASE]
    do_create(db)
    do_read(db)
    do_delete(db)
