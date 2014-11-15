import scrapy

class LoginCrawlItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    url = scrapy.Field()
    host = scrapy.Field()
    raw_html = scrapy.Field()
    
class AuthInfoItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    url = scrapy.Field()
    host = scrapy.Field()
    auth_headers = scrapy.Field()
    response_url = scrapy.Field()
    response_headers = scrapy.Field()
    request_url = scrapy.Field()
    response_code = scrapy.Field()
    response_meta = scrapy.Field()
    request_meta = scrapy.Field()
    response_body = scrapy.Field()