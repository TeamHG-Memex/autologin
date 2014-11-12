import scrapy
from urlparse import urlparse
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule

class LogincrawlItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    url = scrapy.Field()
    host = scrapy.Field()
    raw_html = scrapy.Field()    

class LoginFinderSpider(CrawlSpider):
    
    name = "login_finder"
    rules = (
        # Extract links matching 'item.php' and parse them with the spider's method parse_item
        Rule(LinkExtractor(allow=('.*', )), callback='parse_item'),
    )
    start_urls = []
    allowed_domains = []

    def __init__(self, seed_url, *args, **kwargs):
        
        self.start_urls.append(seed_url)
        super(LoginFinderSpider, self).__init__(*args, **kwargs)
        #!note yet implemented
        max_links_to_follow = 100
        seed_host = urlparse(seed_url).netloc
        self.allowed_domains.append(seed_host)
        print self.allowed_domains
    
    def parse_item(self, response):
        item = LogincrawlItem()
        item["url"] = response.url
        item["host"] = urlparse(response.url)
        item["raw_html"] = response.body
        return item