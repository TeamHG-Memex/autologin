from __future__ import absolute_import
from six.moves.urllib.parse import urlsplit, urlunsplit

import formasaurus
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.settings import Settings
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.exceptions import CloseSpider

from .app import app, db
from .login_keychain import get_domain


settings = Settings(values=dict(
    ROBOTSTXT_OBEY = False,
    DEPTH_LIMIT = 3,
    DOWNLOAD_DELAY = 2.0,
    DEPTH_PRIORITY = 1,
    CONCURRENT_REQUESTS = 2,
    CONCURRENT_REQUESTS_PER_DOMAIN = 2,
    SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue',
    SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue',
    ))
configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})
crawl_runner = CrawlerRunner(settings)


class Spider(scrapy.Spider):
    name = 'spider'
    priority_patterns = [
        # Login links
        'login',
        'logon',
        'signin',
        'sign in',
        # Registration links
        'signup',
        'sign up',
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
        super(Spider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.start_urls:
            yield self.request(url)

    def request(self, url, **kwargs):
        return scrapy.Request(url, callback=self.parse, **kwargs)

    def parse(self, response):
        url = response.url
        self.logger.info(url)
        if response.text:
            for _, meta in formasaurus.extract_forms(response.text):
                form_type = meta['form']
                if form_type == 'login' and not self.found_login:
                    self.found_login = True
                    self.handle_login_form(url)
                elif form_type == 'registration' \
                        and not self.found_registration:
                    self.found_registration = True
                    self.handle_registration_form(url)
        if self.found_registration and self.found_login:
            raise CloseSpider('done')
        for link in self.link_extractor.extract_links(response):
            priority = 0
            text = ' '.join([relative_url(link.url), link.text]).lower()
            if any(pattern in text for pattern in self.priority_patterns):
                priority = 100
            yield self.request(link.url, priority=priority)

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


def relative_url(url):
    parts = urlsplit(url)
    return urlunsplit(('', '') + parts[2:])
