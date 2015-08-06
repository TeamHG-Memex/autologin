import scrapy
from scrapy.utils.response import open_in_browser
from urlparse import urlparse
from loginform.loginform import LoginFormFinder
from scrapy.http import FormRequest
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from crawler.logincrawl.items import AuthInfoItem
from crawler.logincrawl.items import LoginCrawlItem
import tldextract
import traceback
import json
import os
import pickledb
import logging

class LoginFinderSpider(CrawlSpider):
    
    name = "login_finder"
    rules = (
        Rule(LinkExtractor(allow=('.*', )), callback='parse_item'),
    )
    start_urls = []
    allowed_domains = []

    def __init__(self, seed_url, username, password, db_name, use_formasaurus, *args, **kwargs):
        
        self.start_urls.append(seed_url)
        super(LoginFinderSpider, self).__init__(*args, **kwargs)
        #!not yet implemented
        max_links_to_follow = 100
        seed_host = urlparse(seed_url).netloc
        tldextracted = tldextract.extract(seed_url)
        allowed_domain =  '%s.%s' % (tldextracted.domain, tldextracted.sufix)
        self.allowed_domains.append(allowed_domain)
        self.form_extractor = None
        self.username = username
        self.password = password
        self.db_name = db_name
        if use_formasaurus == '1':
            from formasaurus import FormExtractor
            self.form_extractor = FormExtractor.load()


    def parse_item(self, response):
        item = LoginCrawlItem()
        item["url"] = response.url
        item["host"] = urlparse(response.url).netloc
        item["raw_html"] = response.body
        try:
            lff = LoginFormFinder(response.url, response.body, self.username, self.password, self.form_extractor)
            args, url, method = lff.fill_top_login_form()

            #sometimes this callback in the FormRequest is not called! Why?
            fr = FormRequest(url, method=method, formdata=args, callback=self.after_login_attempt, dont_filter=True)
            return fr
        except:
            return item
    
    def after_login_attempt(self, response):
        self.logger.info('Parse function called on %s', response.url)
        item = AuthInfoItem()
        item["response_url"] = response.url
        item["host"] = urlparse(response.url).netloc
        item["response_headers"] = response.headers
        item["auth_headers"] = response.request.headers
        item["request_url"] = response.request.url
        item["response_code"] = response.status
        item["request_meta"] = response.request.meta
        item["response_meta"] = response.meta
        item["response_body"] = response.body
        #open_in_browser(response)

        return item
