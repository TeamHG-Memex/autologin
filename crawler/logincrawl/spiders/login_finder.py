import scrapy
from scrapy.utils.response import open_in_browser
from urlparse import urlparse
from loginform.loginform import LoginFormFinder
from scrapy.http import FormRequest
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule
from crawler.logincrawl.items import AuthInfoItem
from crawler.logincrawl.items import LoginCrawlItem
import traceback
import json
import os
import pickledb

class LoginFinderSpider(CrawlSpider):
    
    name = "login_finder"
    rules = (
        # Extract links matching 'item.php' and parse them with the spider's method parse_item
        Rule(LinkExtractor(allow=('.*', )), callback='parse_item'),
    )
    start_urls = []
    allowed_domains = []

    def __init__(self, seed_url, username, password, *args, **kwargs):
        
        self.start_urls.append(seed_url)
        super(LoginFinderSpider, self).__init__(*args, **kwargs)
        #!not yet implemented
        max_links_to_follow = 100
        seed_host = urlparse(seed_url).netloc
        self.allowed_domains.append(seed_host)
        self.username = username
        self.password = password

    def parse_item(self, response):
        
        item = LoginCrawlItem()
        item["url"] = response.url
        item["host"] = urlparse(response.url).netloc
        item["raw_html"] = response.body

        try:
            lff = LoginFormFinder(response.url, response.body, self.username, self.password)
            args, url, method = lff.fill_top_login_form()

            #sometimes this callback in the FormRequest is not called! Why?
            fr = FormRequest(url, method=method, formdata=args, callback=self.after_login_attempt, dont_filter=True)
            return fr
        except:
            return item
    
    def after_login_attempt(self, response):
        
        #print "Here I am after login for %s with a response code of " % (response.request.url, response.code)
        print "here i am after login"
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
#        open_in_browser(response)

        return item