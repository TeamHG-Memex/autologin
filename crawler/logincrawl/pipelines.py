# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json
import traceback
from loginform import LoginFormFinder
from logincrawl.items import AuthInfoItem
import pickledb

class LoginCrawlPipeline(object):

    def __init__(self):
        print "hello"
        self.db_location = "/tmp/autologin.db"
        self.db = pickledb.load(self.db_location, False)
        self.db.lcreate("auth_urls")

    def process_item(self, item, spider):
        #add url to list of keys/urls
        if isinstance(item, AuthInfoItem):
            if item["response_url"] not in self.db.lgetall("auth_urls"):
                self.db.ladd("auth_urls", item["response_url"])
                self.db.set(item["response_url"], dict(item))
                self.db.dump()