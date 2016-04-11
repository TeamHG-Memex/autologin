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
from scrapy_splash import SplashRequest

from .app import app, db
from .login_keychain import get_domain


LOGIN_FIELD_TYPES = {'username', 'email', 'username or email'}
CHECK_CHECKBOXES = {'remember me checkbox'}
PASSWORD_FIELD_TYPES = {'password'}
SUBMIT_TYPES = {'submit button'}
DEFAULT_POST_HEADERS = {b'Content-Type': b'application/x-www-form-urlencoded'}


base_settings = Settings(values=dict(
    TELNETCONSOLE_ENABLED = False,
    ROBOTSTXT_OBEY = False,
    DEPTH_LIMIT = 3,
    DOWNLOAD_DELAY = 2.0,
    DEPTH_PRIORITY = 1,
    CONCURRENT_REQUESTS = 2,
    CONCURRENT_REQUESTS_PER_DOMAIN = 2,
    SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue',
    SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue',
    CLOSESPIDER_PAGECOUNT = 2000,
    # DOWNLOADER_MIDDLEWARES are set in crawl_runner
    DOWNLOAD_MAXSIZE = 1*1024*1024,  # 1MB
    USER_AGENT = (
            'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Ubuntu Chromium/43.0.2357.130 '
            'Chrome/43.0.2357.130 Safari/537.36'
        ),
    ))
configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})


def crawl_runner(splash_url=None):
    settings = base_settings.copy()
    if splash_url:
        settings['SPLASH_URL'] = splash_url
        settings['DUPEFILTER_CLASS'] = 'scrapy_splash.SplashAwareDupeFilter'
        settings['DOWNLOADER_MIDDLEWARES'] = {
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression'
                '.HttpCompressionMiddleware': 810,
        }
    else:
        settings['DOWNLOADER_MIDDLEWARES'] = {
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
            'autologin.middleware.ExposeCookiesMiddleware': 700,
        }
    return CrawlerRunner(settings)


class DefaultExecuteSplashRequest(SplashRequest):
    '''
    This is a SplashRequest subclass that uses minimal default body
    for the execute endpoint with support for POST requests and cookies.
    '''
    SPLASH_SCRIPT = '''
    function main(splash)
        splash:init_cookies(splash.args.cookies)
        local ok, reason = splash:go{
            splash.args.url,
            headers=splash.args.headers,
            http_method=splash.args.http_method,
            body=splash.args.body,
        }
        if ok then
            assert(splash:wait(0.5))
        end

        local entries = splash:history()
        if #entries > 0 then
            local last_response = entries[#entries].response
            return {
                headers=last_response.headers,
                cookies=splash:get_cookies(),
                html=splash:html(),
                http_status=last_response.status,
            }
        else
            assert(false, reason)
        end
    end
    '''

    def __init__(self, *args, **kwargs):
        kwargs['endpoint'] = 'execute'
        splash_args = kwargs.setdefault('args', {})
        splash_args['lua_source'] = self.SPLASH_SCRIPT
        super(DefaultExecuteSplashRequest, self).__init__(*args, **kwargs)


class BaseSpider(scrapy.Spider):
    def __init__(self, use_splash=False, *args, **kwargs):
        self.request = DefaultExecuteSplashRequest if use_splash else \
                       scrapy.Request
        super(BaseSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.start_urls:
            yield self.request(url, callback=self.parse)


class FormSpider(BaseSpider):
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

        return self.request(params['url'], self.parse_login,
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
        return {'ok': True, 'cookies': cookies, 'start_url': response.url}

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
    fields = list(meta['fields'].items())

    login_field = password_field = None
    for field_name, field_type in fields:
        if field_type in LOGIN_FIELD_TYPES:
            login_field = field_name
        elif field_type in PASSWORD_FIELD_TYPES:
            password_field = field_name

    if login_field is None or password_field is None:
        return

    for field_name, field_type in fields:
        if field_type in CHECK_CHECKBOXES:
            try:
                form.fields[field_name] = 'on'
            except ValueError:
                pass  # This could be not a checkbox after all

    form.fields[login_field] = login
    form.fields[password_field] = password

    submit_values = form.form_values()

    for field_name, field_type in fields:
        if field_type in SUBMIT_TYPES:
            submit_values.append((field_name, form.fields[field_name]))

    return dict(
        url=urljoin(url, form.action),
        method=form.method,
        headers=DEFAULT_POST_HEADERS.copy() if form.method == 'POST' else {},
        body=urlencode(submit_values),
    )


def _cookie_dicts(response):
    if hasattr(response, 'cookiejar'):  # using splash
        cookiejar = response.cookiejar
    else:  # using ExposeCookiesMiddleware
        cookiejar = get_cookiejar(response)
    if cookiejar is None:
        return None
    return [c.__dict__ for c in cookiejar]


def _cookie_tuples(cookie_dicts):
    return [(c['name'], c['value'], c['domain'], c['path'], c['port'])
            for c in cookie_dicts]
