from twisted.internet import reactor
from twisted.internet.error import ReactorNotRunning
from scrapy.crawler import Crawler
#from scrapy import log, signals
from scrapy import  signals
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
import logging
#import importlib
#settings_module = importlib.import_module('crawler.logincrawl.settings')
#settings = Settings(settings_module)
#crawler_settings = CrawlerSettings(settings_module)

class AutoLogin(object):
    
    def __init__(self, db_name):

        self.db_name = db_name
    
    def get_auth_info(self):

        #run login spider, saves results to /tmp/autologin.db
        #self.__run_login_spider(seed_url = self.seed_url, username = self.username, password = self.password)

        #determine header that looks most reasonable as login header and return it
        ahf = AuthHeaderFinder(self.db_name)
        try:
            auth_info = ahf.get_auth_header()
        except:
            logging.critical("No valid login headers found. Here is the traceback: ")
            traceback.print_exc()
            raise Exception("No valid login headers found.")

        #redirected_to = auth_info["response_url"]
        #auth_headers = auth_info["auth_headers"]
        logging.info("Got auth headers %s" % json.dumps(auth_info["auth_headers"]))

        return auth_info
        #return auth_headers, redirected_to

    def return_authenticated_request_item(self, callback = None, meta = None):
        
        auth_info = self.get_auth_info()
        auth_headers = auth_info['auth_headers']
        redirected_to = auth_info['response_url']

        logging.info("Returning auth headers %s and redirected_to url %s" % (json.dumps(auth_headers), str(redirected_to)))
        if callback:
            return Request(redirected_to, callback = callback, meta = meta, headers = auth_headers)
        else:
            return Request(redirected_to, meta = meta, headers = auth_headers)

#usage: the login_finder spider must be run and a database populated with AuthInfoItems for AutoLogin object to work
def init_db(db_name):
    try:
        os.remove(db_name)
    except:
        pass
    db = pickledb.load(db_name, False)
    db.dump()

def run_login_spider(seed_url, username, password, db_name, logfile = "results.log", use_formasaurus = '1'):
    # Check that we can import Formasaurs, fallback to scoring method
    if use_formasaurus == '1':
        try:
            from formasaurus import FormExtractor
            logging.info("Formasaurus is active. We have AI :-)")
        except:
            logging.warning("Formasaurus could not be imported. No AI :-( Falling back to naive scoring method")
            use_formasaurus = '0' 

    init_db(db_name)
    settings = get_project_settings()
    runner = CrawlerRunner(settings)
    d = runner.crawl(LoginFinderSpider, seed_url = seed_url, username = username, password = password, db_name = db_name, use_formasaurus = use_formasaurus)
    d.addBoth(lambda _: reactor.stop())
    logging.info("Item pipelines enabled: %s" % str(settings.get("ITEM_PIPELINES")))
    reactor.run()

if __name__ == "__main__":
    db_name = "eawfwefawefaewweeawf.db"
    logfile = 'results.log'
    logging.basicConfig(filename=logfile,level=logging.DEBUG)
    use_formasaurus = '1' 
    open_in_browser = '1'
    sites = {
            'https://github.com': ['actest1234', 'passpasspass123'],
            'https://www.signupgenius.com': ['actest@hyperiongray.com', 'passpasspass123'],
            'https://twitter.com': ['ghostshell1010', 'B00msh4k3th3r00m!'],
            'https://foursquare.com': ['ghostintheshell1010@gmail.com', 'B00msh4k3th3r00m!'],
            'https://www.tumblr.com': ['ghostintheshell1010@gmail.com', 'password=B00msh4k3th3r00m!'],
            'https://google.com': ['ghostintheshell1010@gmail.com', 'password=B00msh4k3th3r00m!'],
            }
    site = 'https://twitter.com'
    #site = 'https://twitter.com'
    user =  sites[site][0]
    password = sites[site][1]
    print 'Running login spider'
    run_login_spider(site, user, password, db_name, logfile = logfile, use_formasaurus = use_formasaurus)
    al = AutoLogin(db_name)
    req = al.return_authenticated_request_item()
    auth_info = al.get_auth_info()
    logging.info("Request object returned: %s" % req.url)
    logging.info("Request object returned: %s" % req.headers)
    print ("Request object returned: %s" % req.url)
    print ("Request object returned: %s" % req.headers)
    if open_in_browser == "1":
        import webbrowser
        print 'Opening browser'
        tmp_response_file = "/tmp/openinbrowser.html" 
        f = open(tmp_response_file, "w")
        f.write(auth_info["response_body"].encode("utf-8"))
        webbrowser.open(tmp_response_file, new = 2)

    try:
        reactor.stop()
    except ReactorNotRunning:
        pass
