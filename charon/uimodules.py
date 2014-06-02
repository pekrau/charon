" Charon: UI modules. "

import tornado.web

from . import constants


class Icon(tornado.web.UIModule):
    "HTML for an icon, optionally labelled with a title."

    template = """<img src="{url}" class="icon" alt="{alt}" title="{title}">"""

    def render(self, name, title=None, label=False):
        if not name:
            name = 'unknown'
        elif not isinstance(name, basestring):
            name = name[constants.DB_DOCTYPE]
        Name = name.capitalize()
        value = self.template.format(url=self.handler.static_url(name + '.png'),
                                     alt=Name,
                                     title=title or Name)
        if label:
            value += ' ' + (title or Name)
        return value


class Doc(tornado.web.UIModule):
    "HTML for a linkified document."

    iconfilename = None
    keyfield = '_id'

    template = """<a href="{url}">""" \
        """<img src="{src}" class="icon" alt="{title}" title="{title}">""" \
        """ {title}</a>"""

    def render(self, doc):
        self.doc = doc
        return self.template.format(
            url=self.handler.reverse_url(self.__class__.__name__.lower(),
                                         doc[self.keyfield]),
            src=self.handler.static_url(self.iconfilename),
            title=self.get_title())

    def get_title(self):
        try:
            return self.doc['name']
        except KeyError:
            return self.doc['_id']


class Submit(tornado.web.UIModule):
    "HTML for a submit button with an icon, optionally with a different title."

    def render(self, name, title=None, onclick=None):
        if onclick:
            result = """<button type="submit" onclick="{0}">""".format(onclick)
        else:
            result = """<button type="submit">"""
        Name = name.capitalize()
        result += """<img src="{url}" alt="{name}" title="{name}">""".format(
            url=self.handler.static_url(name + '.png'),
            name=Name)
        result += ' ' + (title or Name)
        result += '</button>'
        return result
