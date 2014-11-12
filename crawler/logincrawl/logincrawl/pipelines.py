# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json
from loginform import fill_login_form

class LogincrawlPipeline(object):
    
    def __init__(self):
        self.file = "testout.json"
        self.url_scores = {}
        
    def process_item(self, item, spider):
        username = "user1"
        password = "abc123"
        form_values, form_action, form_method = fill_login_form(item.url, item.raw_html, username, password)
        item["form_values"] = form_values
        item["form_action"] = form_action
        item["form_method"] = form_method
        
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line)        
        
        return item