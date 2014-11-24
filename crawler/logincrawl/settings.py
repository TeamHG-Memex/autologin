# -*- coding: utf-8 -*-

# Scrapy settings for logincrawl project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'logincrawl'

SPIDER_MODULES = ['crawler.logincrawl.spiders']
NEWSPIDER_MODULE = 'crawler.logincrawl.spiders'

#grab max of 1000 pages on site looking for login
CLOSESPIDER_ITEMCOUNT = '100'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:33.0) Gecko/20100101 Firefox/33.0'
ITEM_PIPELINES = {
    'crawler.logincrawl.pipelines.LoginCrawlPipeline': 800
}
