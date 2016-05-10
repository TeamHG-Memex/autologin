from __future__ import absolute_import
from six.moves.urllib.parse import urlsplit

from flask_admin.contrib import sqla
from sqlalchemy.exc import IntegrityError

from .app import db


class KeychainItem(db.Model):
    __tablename__ = 'keychain_item'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # URLs (all having the same domain)
    domain = db.Column(db.String(255), nullable=False, unique=True)
    start_url = db.Column(db.Text(), nullable=False)
    login_url = db.Column(db.Text(), nullable=False, default='')
    registration_url = db.Column(db.Text(), nullable=False, default='')
    # Login credentials (or marked as a skip)
    skip = db.Column(db.Boolean, default=False, nullable=False)
    login = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), nullable=True)

    @classmethod
    def add_task(cls, url):
        ''' Create credentials task. Return created item if it was created,
        or None if an item for the given domain already existed.
        '''
        item = cls(domain=get_domain(url), start_url=url)
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
        return (
            db.session.query(cls)
            .filter(cls.domain == get_domain(url))
            .one_or_none())

    def __unicode__(self):
        return '%s: %s' % (self.domain, self.login)

    @property
    def solved(self):
        return (
            self.login_url
            and self.login is not None
            and self.password is not None)

    @property
    def link(self):
        url = self.start_url
        if self.login:
            if self.login_url:
                url = self.login_url
        elif self.registration_url and not self.skip:
            url = self.registration_url
        return url


def get_domain(url):
    return urlsplit(url).netloc


class KeychainItemAdmin(sqla.ModelView):
    column_list = ['link', 'skip', 'login', 'password']
    column_labels = {
        'skip': 'Skip?',
    }
    column_editable_list = ['skip', 'login', 'password']
    column_searchable_list = ['domain']
