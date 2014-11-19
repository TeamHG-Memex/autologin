from twisted.internet import reactor
from scrapy.crawler import Crawler
from scrapy import log, signals
from scrapy.utils.project import get_project_settings
from crawler.logincrawl.spiders.login_finder import LoginFinderSpider
import sys
from auth_analysis.auth_analysis import AuthHeaderFinder
from scrapy.xlib.pydispatch import dispatcher
import crawler.logincrawl.settings
import json
import os
os.environ["SCRAPY_SETTINGS_MODULE"] = "crawler.logincrawl.settings"
import pickledb
from scrapy import Request as Request
from scrapy.settings import Settings
import traceback
from scrapy.crawler import CrawlerRunner
#import importlib
#settings_module = importlib.import_module('crawler.logincrawl.settings')
#settings = Settings(settings_module)
#crawler_settings = CrawlerSettings(settings_module)

class AutoLogin(object):
    
    def get_auth_headers_and_redirect_url(self):

        #run login spider, saves results to /tmp/autologin.db
        #self.__run_login_spider(seed_url = self.seed_url, username = self.username, password = self.password)

        #determine header that looks most reasonable as login header and return it
        ahf = AuthHeaderFinder()
        try:
            auth_info = ahf.get_auth_header()
        except:
            log.msg("No valid login headers found. Here is the traceback: ", level = log.CRITICAL)
            traceback.print_exc()
            raise Exception("No valid login headers found.")
            
        redirected_to = auth_info["response_url"]
        auth_headers = auth_info["auth_headers"]
        log.msg("Got auth headers %s" % json.dumps(auth_headers))

        return auth_headers, redirected_to
    
    def return_authenticated_request_item(self, callback = None, meta = None):
    
        auth_headers, redirected_to = self.get_auth_headers_and_redirect_url()
        log.msg("Returning auth headers %s and redirected_to url %s" % (json.dumps(auth_headers), str(redirected_to)), level = log.INFO)
        if callback:
            return Request(redirected_to, callback = callback, meta = meta, headers = auth_headers)
        else:
            return Request(redirected_to, meta = meta, headers = auth_headers)

#usage: the login_finder spider must be run and a database populated with AuthInfoItems for AutoLogin object to work
def init_db(db_file = "/tmp/autologin.db"):
    os.remove(db_file)
    db = pickledb.load(db_file, False)
    db.dump()

def run_login_spider(seed_url, username, password, logfile = "results.log"):

    init_db()
    settings = get_project_settings()
    runner = CrawlerRunner(settings)
    d = runner.crawl(LoginFinderSpider, seed_url = seed_url, username = username, password = password)
    d.addBoth(lambda _: reactor.stop())
    log.start(loglevel=log.DEBUG, logfile=logfile)
    log.msg("Item pipelines enabled: %s" % str(settings.get("ITEM_PIPELINES")), level = log.INFO)
    reactor.run()

if __name__ == "__main__":

    run_login_spider("https://github.com/", "actest1234", "passpasspass123", logfile = "results.log")
    al = AutoLogin()
    req = al.return_authenticated_request_item()
    log.msg("Request object returned: %s" % req.url)
    log.msg("Request object returned: %s" % req.headers)