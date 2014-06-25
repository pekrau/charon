" Charon: Context handler for saving a document. "

import logging

import couchdb

from . import constants
from . import utils


class DocumentSaver(object):
    "Abstract context handler creating or updating a document."

    doctype = None
    field_keys = []

    def __init__(self, doc=None, rqh=None, db=None):
        assert self.doctype
        if rqh is not None:
            self.rqh = rqh
            self.db = rqh.db
            self.current_user = rqh.current_user
        elif db is not None:
            self.db = db
            self.current_user = dict()
        else:
            raise ValueError('neither db nor rqh given')
        self.doc = doc or dict()
        self.changed = dict()
        self.deleted = dict()
        if '_id' in self.doc:
            assert self.doctype == self.doc[constants.DB_DOCTYPE]
        else:
            self.doc['_id'] = utils.get_iuid()
            self.doc[constants.DB_DOCTYPE] = self.doctype
            self.initialize()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if type is not None: return False # No exceptions handled here
        self.finalize()
        try:
            self.db.save(self.doc)
        except couchdb.http.ResourceConflict:
            raise IOError('document revision update conflict')
        utils.log(self.db, self.doc,
                  changed=self.changed,
                  deleted=self.deleted,
                  current_user=self.current_user)

    def __setitem__(self, key, value):
        "Update the key/value pair."
        try:
            checker = getattr(self, "check_{0}".format(key))
        except AttributeError:
            pass
        else:
            checker(value)
        try:
            converter = getattr(self, "convert_{0}".format(key))
        except AttributeError:
            pass
        else:
            value = converter(value)
        try:
            if self.doc[key] == value:
                logging.debug("Saver.__setitem__() equal")
                return
        except KeyError:
            pass
        logging.debug("Saver.__setitem__(%s, %s", key, value)
        self.doc[key] = value
        self.changed[key] = value

    def __getitem__(self, key):
        return self.doc[key]

    def __delitem__(self, key):
        self.deleted[key] = self.doc[key]
        del self.doc[key]

    def initialize(self):
        "Perform actions when creating the document."
        self.doc['created'] = utils.timestamp()

    def is_new(self):
        "Is the document new, i.e. not previously saved in the database?"
        return '_rev' not in self.doc

    def finalize(self):
        "Perform any final modifications before saving the document."
        self.doc['modified'] = utils.timestamp()

    def update(self, data=None):
        """Update the fields from either the explicit data dictionary,
        or the HTML form parameters."""
        for key in self.field_keys:
            if data is None:
                self[key] = self.rqh.get_argument(key, None)
            else:
                self[key] = data.get(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
