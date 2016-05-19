from __future__ import absolute_import
from base64 import b64decode
from collections import namedtuple
from functools import partial
import logging
import os.path
import uuid
from six.moves.urllib.parse import urlsplit, urlunsplit, urlencode, urljoin

import formasaurus
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.settings import Settings
from scrapy.crawler import CrawlerRunner
from scrapy.exceptions import CloseSpider
from scrapy.utils.response import get_base_url
from scrapy_splash import SplashRequest
from twisted.internet.defer import inlineCallbacks, returnValue

from .middleware import get_cookiejar
from .app import app, db, server_path
from .login_keychain import get_domain


USERNAME_FIELD_TYPES = {'username', 'email', 'username or email'}
CHECK_CHECKBOXES = {'remember me checkbox'}
PASSWORD_FIELD_TYPES = {'password'}
CAPTCHA_FIELD_TYPES = {'captcha'}
SUBMIT_TYPES = {'submit button'}
DEFAULT_POST_HEADERS = {b'Content-Type': b'application/x-www-form-urlencoded'}

USER_AGENT = (
    'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Ubuntu Chromium/43.0.2357.130 '
    'Chrome/43.0.2357.130 Safari/537.36'
)

base_settings = Settings(values=dict(
    TELNETCONSOLE_ENABLED = False,
    ROBOTSTXT_OBEY = False,
    DOWNLOAD_DELAY = 2.0,
    DEPTH_PRIORITY = 1,
    CONCURRENT_REQUESTS = 2,
    CONCURRENT_REQUESTS_PER_DOMAIN = 2,
    SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue',
    SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue',
    # DOWNLOADER_MIDDLEWARES are set in get_settings
    USER_AGENT = USER_AGENT,
    DOWNLOADER_MIDDLEWARES = {
        'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,
        'autologin.middleware.ProxyFromSettingsMiddleware': 750,
    },
))


def crawl_runner(extra_settings=None):
    settings = base_settings.copy()
    if extra_settings is not None:
        settings.update(extra_settings, priority='cmdline')
    if settings.get('SPLASH_URL'):
        settings['DUPEFILTER_CLASS'] = 'scrapy_splash.SplashAwareDupeFilter'
        settings.setdefault('DOWNLOADER_MIDDLEWARES', {}).update({
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression'
                '.HttpCompressionMiddleware': 810,
        })
    else:
        settings.setdefault('DOWNLOADER_MIDDLEWARES', {}).update({
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
            'autologin.middleware.ExposeCookiesMiddleware': 700,
        })
    return CrawlerRunner(settings)


def splash_request(lua_source, *args, **kwargs):
    kwargs['endpoint'] = 'execute'
    splash_args = kwargs.setdefault('args', {})
    splash_args['lua_source'] = lua_source
    splash_args['timeout'] = 60
    extra_js = kwargs.pop('extra_js', None)
    if extra_js:
        splash_args['extra_js'] = extra_js
    return SplashRequest(*args, **kwargs)


class BaseSpider(scrapy.Spider):
    """
    Base spider.
    It uses Splash for requests if SPLASH_URL is not None or empty.
    """
    lua_source = 'default.lua'

    def __init__(self, *args, **kwargs):
        self.extra_js = kwargs.pop('extra_js', None)
        super(BaseSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        self._finish_init()
        for url in self.start_urls:
            yield self.request(url)

    def _finish_init(self):
        self.using_splash = bool(self.settings.get('SPLASH_URL'))
        if self.using_splash:
            with open(os.path.join(
                    os.path.dirname(__file__), 'directives', self.lua_source),
                    'rb') as f:
                lua_source = f.read().decode('utf-8')
            self.request = partial(
                splash_request, lua_source,
                extra_js=self.extra_js)
        else:
            if self.extra_js:
                raise ValueError(
                    '"extra_js" not supported without "SPLASH_URL"')
            self.request = scrapy.Request


class FormSpider(BaseSpider):
    """
    This spider crawls a website trying to find login and registration forms.
    When a form is found, its URL is saved to the database.
    """
    name = 'forms'
    custom_settings = {
        'DEPTH_LIMIT': 3,
        'CLOSESPIDER_PAGECOUNT': 2000,
        'DOWNLOAD_MAXSIZE': 1*1024*1024,  # 1MB
    }
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
            yield self.request(link.url, self.parse, priority=priority)

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


class LoginSpider(BaseSpider):
    """ This spider tries to login and returns an item with login cookies. """
    name = 'login'
    lua_source = 'login.lua'
    custom_settings = {
        'DEPTH_LIMIT': 0,  # retries are tracked explicitly
        'LOGIN_MAX_RETRIES': 10,
        'DECAPTCHA_DEATHBYCAPTCHA_USERNAME':
            os.environ.get('DEATHBYCAPTCHA_USERNAME'),
        'DECAPTCHA_DEATHBYCAPTCHA_PASSWORD':
            os.environ.get('DEATHBYCAPTCHA_PASSWORD'),
    }

    def __init__(self, url, username, password, *args, **kwargs):
        self.start_url = url
        self.start_urls = [self.start_url]
        self.username = username
        self.password = password
        self.solver = None
        self.retries_left = None
        self.attempted_captchas = []
        super(LoginSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        self._finish_init()
        settings = self.crawler.settings
        self.solver = None
        try:
            import decaptcha
        except ImportError:
            self.logger.warning('Decaptcha not installed')
        else:
            from decaptcha.solvers.deathbycaptcha import DeathbycaptchaSolver
            if (settings.get('DECAPTCHA_DEATHBYCAPTCHA_USERNAME') and
                    settings.get('DECAPTCHA_DEATHBYCAPTCHA_PASSWORD')):
                self.solver = DeathbycaptchaSolver(self.crawler)
            else:
                self.logger.warning('DeathByCaptcha account not provided')
        self.retries_left = settings.getint('LOGIN_MAX_RETRIES')
        request_kwargs = {}
        if self.using_splash:
            request_kwargs['args'] = {'full_render': True}
        yield self.request(self.start_url, **request_kwargs)

    def retry(self, tried_login=False, retry_once=False):
        self.retries_left -= 1
        if retry_once:
            self.retries_left = min(1, self.retries_left)
        if self.retries_left:
            self.logger.debug('Retrying login')
            return self.request(
                self.start_url,
                callback=partial(self.parse, tried_login=tried_login),
                dont_filter=True)
        else:
            self.logger.debug('No retries left, giving up')

    @inlineCallbacks
    def parse(self, response, tried_login=False):
        initial_cookies = _response_cookies(response)
        page_forms = response.data.get('forms') if self.using_splash else None
        if page_forms:
            page_forms = _from_lua(page_forms)
        forminfo = get_login_form(response.text, page_forms=page_forms)
        if forminfo is None:
            if tried_login and initial_cookies:
                # If we can not find a login form on retry, then we must
                # have already logged in, but the cookies did not change,
                # so we did not detect our success.
                yield self.report_captchas()
                returnValue({
                    'ok': True,
                    'cookies': initial_cookies,
                    'start_url': response.url})
            returnValue({'ok': False, 'error': 'nologinform'})

        form_idx, form, meta = forminfo
        self.logger.info('found login form: %s' % meta)
        extra_fields = {}
        captcha_solved = False
        captcha_field = _get_captcha_field(meta)
        if captcha_field and page_forms and self.solver:
            captcha_value = yield self.solve_captcha(page_forms[form_idx])
            if captcha_value:
                captcha_solved = True
                extra_fields[captcha_field] = captcha_value
            else:
                returnValue(self.retry())

        params = login_params(
            url=get_base_url(response),
            username=self.username,
            password=self.password,
            form=form,
            meta=meta,
            extra_fields=extra_fields,
        )
        self.logger.debug('submit parameters: %s' % params)

        returnValue(self.request(
            params['url'],
            # If we did not try solving the captcha, retry just once
            # to check if the login form dissapears (and we logged in).
            callback=partial(self.parse_login, retry_once=not captcha_solved),
            method=params['method'],
            headers=params['headers'],
            body=params['body'],
            meta={'initial_cookies': cookie_dicts(initial_cookies) or []},
            dont_filter=True,
        ))

    @inlineCallbacks
    def parse_login(self, response, retry_once=False):
        cookies = _response_cookies(response) or []

        old_cookies = set(_cookie_tuples(response.meta['initial_cookies']))
        new_cookies = set(_cookie_tuples(cookie_dicts(cookies)))

        if self.using_splash:
            self.debug_screenshot('page', b64decode(response.data['page']))
        if new_cookies <= old_cookies:  # no new or changed cookies
            fail = {'ok': False, 'error': 'badauth'}
            returnValue(
                self.retry(tried_login=True, retry_once=retry_once) or fail)
        yield self.report_captchas()
        returnValue({'ok': True, 'cookies': cookies, 'start_url': response.url})

    @inlineCallbacks
    def solve_captcha(self, page_form):
        from decaptcha.exceptions import DecaptchaError
        form_screenshot = b64decode(page_form['screenshot'])
        self.debug_screenshot('captcha', form_screenshot)
        try:
            captcha_value = yield self.solver.solve(form_screenshot)
        except DecaptchaError as e:
            self.logger.error('captcha not solved', exc=e)
            returnValue(None)
        else:
            self.logger.debug('captcha solved: "%s"' % captcha_value)
            self.attempted_captchas.append(form_screenshot)
            returnValue(captcha_value)

    @inlineCallbacks
    def report_captchas(self):
        # We assume that if we have logged in, then all previous failed attempts
        # were due to incorrectly solved captchas.
        if self.attempted_captchas:
            for captcha_image in self.attempted_captchas[:-1]:
                yield self.solver.report(captcha_image)
            self.attempted_captchas = []

    def debug_screenshot(self, name, screenshot):
        if not self.logger.isEnabledFor(logging.DEBUG):
            return
        browser_dir = os.path.join(server_path, 'static/browser')
        filename = os.path.join(browser_dir, '{}.jpeg'.format(uuid.uuid4()))
        with open(filename, 'wb') as f:
            f.write(screenshot)
        self.logger.debug('saved %s screenshot to %s' % (name, filename))


def get_login_form(html_source, page_forms=None):
    matches = []
    Match = namedtuple('Match', ['idx', 'form', 'meta'])
    for idx, (form, meta) in enumerate(formasaurus.extract_forms(html_source)):
        if meta['form'] == 'login':
            matches.append(Match(idx, form, meta))
    if matches:
        if page_forms:
            return max(matches, key=lambda match: (
                _get_captcha_field(match.meta) is not None,
                _form_area(page_forms[match.idx])))
        else:
            return matches[0]


def _form_area(form_meta):
    region = form_meta['region']
    left, top, right, bottom = region
    return (right - left) * (bottom - top)


def _from_lua(table):
    return [table[str(idx + 1)] for idx in range(len(table))]


def _get_captcha_field(meta):
    for name, field_type in meta['fields'].items():
        if field_type in CAPTCHA_FIELD_TYPES:
            return name


def relative_url(url):
    parts = urlsplit(url)
    return urlunsplit(('', '') + parts[2:])


def login_params(url, username, password, form, meta, extra_fields=None):
    """
    Return ``{'url': url, 'method': method, 'body': body}``
    with all required information for submitting a login form.
    """
    fields = list(meta['fields'].items())

    username_field = password_field = None
    for field_name, field_type in fields:
        if field_type in USERNAME_FIELD_TYPES:
            username_field = field_name
        elif field_type in PASSWORD_FIELD_TYPES:
            password_field = field_name

    if username_field is None or password_field is None:
        return

    for field_name, field_type in fields:
        if field_type in CHECK_CHECKBOXES:
            try:
                form.fields[field_name] = 'on'
            except ValueError:
                pass  # This could be not a checkbox after all

    form.fields[username_field] = username
    form.fields[password_field] = password
    if extra_fields:
        for k, v in extra_fields.items():
            form.fields[k] = v

    submit_values = form.form_values()

    for field_name, field_type in fields:
        if field_type in SUBMIT_TYPES:
            submit_values.append((field_name, form.fields[field_name]))

    return dict(
        url=form.action if url is None else urljoin(url, form.action),
        method=form.method,
        headers=DEFAULT_POST_HEADERS.copy() if form.method == 'POST' else {},
        body=urlencode(submit_values),
    )


def cookie_dicts(cookiejar):
    if cookiejar is None:
        return None
    return [c.__dict__ for c in cookiejar]


def _response_cookies(response):
    if hasattr(response, 'cookiejar'):  # using splash
        return response.cookiejar
    else:  # using ExposeCookiesMiddleware
        return get_cookiejar(response)


def _cookie_tuples(cookie_dicts_):
    return [(c['name'], c['value'], c['domain'], c['path'], c['port'])
            for c in cookie_dicts_]
