from __future__ import absolute_import
from six.moves.urllib.parse import urlsplit, urlunsplit, urlencode, urljoin

import formasaurus
import scrapy
from autologin.middleware import get_cookiejar
from scrapy.linkextractors import LinkExtractor
from scrapy.settings import Settings
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.exceptions import CloseSpider
from scrapy.utils.response import get_base_url

from .app import app, db
from .login_keychain import get_domain


LOGIN_FIELD_TYPES = {'username', 'email', 'username or email'}
CHECK_CHECKBOXES = {'remember me checkbox'}
PASSWORD_FIELD_TYPES = {'password'}
DEFAULT_POST_HEADERS = {b'Content-Type': b'application/x-www-form-urlencoded'}


settings = Settings(values=dict(
    TELNET_ENABLED = False,
    ROBOTSTXT_OBEY = False,
    DEPTH_LIMIT = 3,
    DOWNLOAD_DELAY = 2.0,
    DEPTH_PRIORITY = 1,
    CONCURRENT_REQUESTS = 2,
    CONCURRENT_REQUESTS_PER_DOMAIN = 2,
    SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue',
    SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue',
    CLOSESPIDER_PAGECOUNT = 2000,
    DOWNLOAD_MAXSIZE = 1*1024*1024,  # 1MB
    DOWNLOADER_MIDDLEWARES = {
        'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
        'autologin.middleware.ExposeCookiesMiddleware': 700,
    },
    USER_AGENT = (
            'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Ubuntu Chromium/43.0.2357.130 '
            'Chrome/43.0.2357.130 Safari/537.36'
        ),
    ))
configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})
crawl_runner = CrawlerRunner(settings)


class FormSpider(scrapy.Spider):
    """
    This spider crawls a website trying to find login and registration forms.
    When a form is found, its URL is saved to the database.
    """
    name = 'forms'
    priority_patterns = [
        # Login links
        'login',
        'log in',
        'logon',
        'signin',
        'sign in',
        'sign-in',
        # Registration links
        'signup',
        'sign up',
        'sign-up',
        'register',
        'registration',
        'account',
        'join',
    ]

    def __init__(self, url, credentials, *args, **kwargs):
        self.credentials = credentials
        self.start_urls = [url]
        self.link_extractor = LinkExtractor(allow_domains=[get_domain(url)])
        self.found_login = False
        self.found_registration = False
        super(FormSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        self.logger.info(response.url)
        if response.text:
            for _, meta in formasaurus.extract_forms(response.text):
                form_type = meta['form']
                if form_type == 'login' and not self.found_login:
                    self.found_login = True
                    self.handle_login_form(response.url)
                elif form_type == 'registration' \
                        and not self.found_registration:
                    self.found_registration = True
                    self.handle_registration_form(response.url)
        if self.found_registration and self.found_login:
            raise CloseSpider('done')
        for link in self.link_extractor.extract_links(response):
            priority = 0
            text = ' '.join([relative_url(link.url), link.text]).lower()
            if any(pattern in text for pattern in self.priority_patterns):
                priority = 100
            yield scrapy.Request(link.url, self.parse, priority=priority)

    def handle_login_form(self, url):
        self.logger.info('Found login form at %s', url)
        with app.app_context():
            self.credentials.login_url = url
            db.session.add(self.credentials)
            db.session.commit()

    def handle_registration_form(self, url):
        self.logger.info('Found registration form at %s', url)
        with app.app_context():
            self.credentials.registration_url = url
            db.session.add(self.credentials)
            db.session.commit()


class LoginSpider(scrapy.Spider):
    """ This spider tries to login and returns an item with login cookies. """
    name = 'login'

    def __init__(self, url, login, password, *args, **kwargs):
        self.start_urls = [url]
        self.login = login
        self.password = password
        super(LoginSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        forminfo = self._get_login_form(response)
        if forminfo is None:
            return {'ok': False, 'error': 'nologinform'}

        form, meta = forminfo
        self.logger.info("found login form: %s" % meta)

        params = login_params(
            url=get_base_url(response),
            login=self.login,
            password=self.password,
            form=form,
            meta=meta
        )
        self.logger.debug("submit parameters: %s" % params)
        initial_cookies = _cookie_dicts(response) or []

        return scrapy.Request(params['url'], self.parse_login,
            method=params['method'],
            headers=params['headers'],
            body=params['body'],
            meta={'initial_cookies': initial_cookies},
        )

    def parse_login(self, response):
        cookies = _cookie_dicts(response) or []

        old_cookies = set(_cookie_tuples(response.meta['initial_cookies']))
        new_cookies = set(_cookie_tuples(cookies))

        if new_cookies <= old_cookies:  # no new or changed cookies
            return {'ok': False, 'error': 'badauth'}
        return {'ok': True, 'cookies': cookies}

    def _get_login_form(self, response):
        for form, meta in formasaurus.extract_forms(response.text):
            if meta['form'] == 'login':
                return form, meta


def relative_url(url):
    parts = urlsplit(url)
    return urlunsplit(('', '') + parts[2:])


def login_params(url, login, password, form, meta):
    """
    Return ``{'url': url, 'method': method, 'body': body}``
    with all required information for submitting a login form.
    """
    login_field = password_field = None
    for field_name, field_type in meta['fields'].items():
        if field_type in LOGIN_FIELD_TYPES:
            login_field = field_name
        elif field_type in PASSWORD_FIELD_TYPES:
            password_field = field_name

    if login_field is None or password_field is None:
        return

    for field_name, field_type in meta['fields'].items():
        if field_type in CHECK_CHECKBOXES:
            form.fields[field_name] = 'on'

    form.fields[login_field] = login
    form.fields[password_field] = password
    return dict(
        url=urljoin(url, form.action),
        method=form.method,
        headers=DEFAULT_POST_HEADERS.copy() if form.method == 'POST' else {},
        body=urlencode(form.form_values()),
    )


def _cookie_dicts(response):
    cookiejar = get_cookiejar(response)
    if cookiejar is None:
        return None
    return [c.__dict__ for c in cookiejar]


def _cookie_tuples(cookie_dicts):
    return [(c['name'], c['value'], c['domain'], c['path'], c['port'])
            for c in cookie_dicts]
