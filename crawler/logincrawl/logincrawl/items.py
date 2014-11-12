# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class LogincrawlItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    url = scrapy.Field()
    host = scrapy.Field()
    link = scrapy.Field()
    raw_html = scrapy.Field()
    auth_headers = scrapy.Field()