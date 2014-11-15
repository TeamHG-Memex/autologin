from twisted.internet import reactor
from scrapy.crawler import Crawler
from scrapy import log, signals
from scrapy.utils.project import get_project_settings
from logincrawl.spiders.login_finder import LoginFinderSpider
import sys
sys.path.append("../")
from auth_analysis.auth_analysis import AuthHeaderFinder
from scrapy.xlib.pydispatch import dispatcher
import json
import os
import pickledb

def init_db(db_file = "/tmp/autologin.db"):
    os.remove(db_file)
    db = pickledb.load(db_file, False)    
    db.dump()

def run_login_spider(seed_url, username, password):
    
    def stop_reactor():
        reactor.stop()

    dispatcher.connect(stop_reactor, signal=signals.spider_closed)
    spider = LoginFinderSpider(seed_url = seed_url, username=username, password = password)
    settings = get_project_settings()
    crawler = Crawler(settings)
    crawler.configure()
    crawler.crawl(spider)
    crawler.start()
    reactor.run()  # the script will block here until the spider is closed    

def authenticate_to_site(seed_url, username, password):

    #run login spider, saves results to /tmp/autologin.db
    run_login_spider(seed_url = seed_url, username=username, password = password)

    #determine header that looks most reasonable as login header and return it
    ahf = AuthHeaderFinder()
    return ahf.get_auth_header()["auth_headers"]
    
if __name__ == "__main__":

    print json.dumps(authenticate_to_site("https://www.python.org/", username = "actest1234", password = "passpasspass123"))