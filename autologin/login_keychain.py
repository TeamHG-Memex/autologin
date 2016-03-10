from __future__ import absolute_import
from six.moves.urllib.parse import urlsplit, urlunsplit

import jinja2
from flask_admin.contrib import sqla
from sqlalchemy import sql
from sqlalchemy.exc import IntegrityError

from .app import db


class KeychainItem(db.Model):
    __tablename__ = 'keychain_item'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Parts of the login url
    scheme = db.Column(db.String(63), nullable=False)
    netloc = db.Column(db.String(255), nullable=False, unique=True)
    path = db.Column(db.Text(), nullable=False, default='')
    query = db.Column(db.Text(), nullable=False, default='')
    fragment = db.Column(db.Text(), nullable=False, default='')
    # Login credentials (or marked as skipped)
    skip = db.Column(db.Boolean, default=False, nullable=False)
    login = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), nullable=True)

    @classmethod
    def add_task(cls, url):
        ''' Create credentials task. Return created item if it was created,
        or None if an item for the given domain already existed.
        '''
        parts = urlsplit(url)
        item = cls(
            scheme=parts.scheme,
            netloc=parts.netloc,
            path=parts.path,
            query=parts.query,
            fragment=parts.fragment,
            skip=False)
        db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        else:
            return item

    @classmethod
    def get_credentials(cls, url):
        ''' Return an item for the given domain, or None.
        '''
        netloc = urlsplit(url).netloc
        return (db.session.query(cls)
            .filter(cls.netloc == netloc)
            .one_or_none())

    @classmethod
    def any_unsolved(cls):
        ''' Are there any unsolved tasks?
        '''
        return db.session.query(sql.exists().where(
            (cls.skip == False) &
            ((cls.login == None) | (cls.password == None))
            )).scalar()

    def __unicode__(self):
        return '%s: %s' % (self.url, self.login)

    @property
    def solved(self):
        return self.login is not None and self.password is not None

    @property
    def url(self):
        return urlunsplit(
            (self.scheme, self.netloc, self.path, self.query, self.fragment))

    @property
    def link(self):
        return jinja2.Markup(
            '<a href="{url}" target="_blank">{url}</a>'.format(url=self.url))



class KeychainItemAdmin(sqla.ModelView):
    column_list = ['link', 'skip', 'login', 'password']
    column_labels = {
        'link': 'URL',
        'skip': 'Skip?',
    }
    column_editable_list = ['skip', 'login', 'password']
    column_searchable_list = ['netloc', 'query']
