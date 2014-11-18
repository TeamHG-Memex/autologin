# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json
import traceback
from loginform.loginform import LoginFormFinder
from crawler.logincrawl.items import AuthInfoItem
import pickledb
from scrapy import log

class LoginCrawlPipeline(object):

    def __init__(self):
        self.db_location = "/tmp/autologin.db"
        self.db = pickledb.load(self.db_location, False)
        self.db.lcreate("auth_urls")
        log.msg("Instantiated db at location %s" % self.db_location, level = log.INFO)

    def process_item(self, item, spider):
        #add url to list of keys/urls
        log.msg("Processing an AuthInfoItem", level = log.INFO)
        
        if isinstance(item, AuthInfoItem):
            if item["response_url"] not in self.db.lgetall("auth_urls"):
                self.db.ladd("auth_urls", item["response_url"])
                self.db.set(item["response_url"], dict(item))
                self.db.dump()