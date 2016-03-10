from __future__ import absolute_import

import formasaurus
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging

from .app import app, db
from .login_keychain import get_domain


crawl_runner = CrawlerRunner()
configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})


# TODO - settings (BFO, max depth, delay, etc)


class Spider(scrapy.Spider):
    name = 'spider'

    def __init__(self, url, credentials, *args, **kwargs):
        self.credentials = credentials
        self.start_urls = [url]
        self.link_extractor = LinkExtractor(allow_domains=[get_domain(url)])
        super(Spider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.start_urls:
            yield self.request(url)

    def request(self, url):
        return scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        url = response.url
        self.logger.info(url)
        if response.text:
            for _, meta in formasaurus.extract_forms(response.text):
                form_type = meta['form']
                if form_type == 'login':
                    self.handle_login_form(url)
                elif form_type == 'form':
                    self.handle_registration_form(url)
        # TODO - request priority
        for link in self.link_extractor.extract_links(response):
            yield self.request(link.url)

    def handle_login_form(self, url):
        self.logger.info('Found login form at %s', url)
        with app.app_context():
            # TODO - update only login_url field
            self.credentials.login_url = url
            db.session.add(self.credentials)
            db.session.commit()

    def handle_registration_form(self, url):
        self.logger.info('Found registration form at %s', url)
        with app.app_context():
            # TODO - update only registration_url field
            self.credentials.registration_url = url
            db.session.add(self.credentials)
            db.session.commit()
