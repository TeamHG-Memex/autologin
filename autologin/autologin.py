#!/usr/bin/env python
from __future__ import absolute_import, print_function
import argparse, pprint, webbrowser

from scrapy.crawler import CrawlerProcess

from .spiders import LoginSpider, get_login_form, login_params, get_settings, \
    USER_AGENT


class AutoLogin(object):
    def auth_cookies_from_url(self, url, username, password, splash_url=None):
        """
        Fetch page, find login form, try to login and return cookies.
        This call is blocking, and we assume that Twisted reactor is not used
        If it is used, for example in a scrapy spider, use HTTP API.
        Non-blocking interface is also possible:
        see http_api.AutologinAPI._login.
        """
        crawler_process = CrawlerProcess(
            get_settings(splash_url=splash_url))
        crawler_process.crawl(
            LoginSpider,
            url=url,
            username=username,
            password=password,
            use_splash=bool(splash_url))
        crawler_process.start()
        # TODO - get items (maybe using scrape_items)

    def login_request(
            self, html_source, username, password, base_url=None):
        """
        Search html_source for login forms, return a form request dictionary.
        The request dictionary contains the form action URL and the data
        to post. The fields returned are: url, method, headers, body.
        """
        forminfo = get_login_form(html_source)
        if forminfo is None:
            return None
        form, meta = forminfo
        return login_params(
            url=base_url,
            username=username,
            password=password,
            form=form,
            meta=meta,
        )


def show_in_browser(url, cookie_jar):
    """
    Get html source, save in /tmp/ directory,
    then show in browser using webbrowser.
    """
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': (
            'text/html,application/xhtml+xml,'
            'application/xml;q-0.9,*/*;q=0.8'
        ),
        'Accept-Language': 'en',
    }
    # TODO - py3 compat
    import urllib2
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
    req = urllib2.Request(url, headers=headers)
    response = opener.open(req, timeout=10)
    html_source = response.read()
    filename = '/tmp/autologin_show_in_browser.html'
    with open(filename, 'w+') as f:
        f.write(html_source)
    webbrowser.open(filename, new=2)


def main():
    """
    Command line utility for extracting authenticated login cookies.
    """
    argparser = argparse.ArgumentParser(add_help=True)
    argparser.add_argument('username', help='login username')
    argparser.add_argument('password', help='login password')
    argparser.add_argument('url', help='url for the site you wish to login to')
    argparser.add_argument('--show-in-browser', '-b',
        help='show page in browser after login (default: False)',
        action='store_true')
    args = argparser.parse_args()
    # Try logging into site
    auto_login = AutoLogin()
    login_cookies = auto_login.auth_cookies_from_url(
        args.url, args.username, args.password)
    # Print extracted cookies
    pprint.pprint(login_cookies.__dict__)
    # Open browser tab with page using cookies
    if args.show_in_browser:
        show_in_browser(args.url, login_cookies)


if __name__ == '__main__':
    main()
