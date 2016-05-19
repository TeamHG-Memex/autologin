#!/usr/bin/env python
from __future__ import absolute_import, print_function
import argparse, pprint, webbrowser

import crochet
import requests
from scrapy.utils.log import configure_logging

from .spiders import LoginSpider, get_login_form, login_params, crawl_runner, \
    USER_AGENT
from .scrapyutils import scrape_items


__all__ = ['AutoLoginException', 'AutoLogin']


class AutoLoginException(Exception):
    pass


class AutoLogin(object):
    def auth_cookies_from_url(self, url, username, password,
                              extra_js=None, settings=None):
        """
        Fetch page, find login form, try to login and return cookies.
        This call is blocking, and we assume that Twisted reactor is not used.
        If it is used, for example in a scrapy spider, use the HTTP API.
        Non-blocking interface is also possible:
        see http_api.AutologinAPI._login.
        :return: cookie jar, or raise an AutoLoginException with reason.
        """
        crochet.setup()
        @crochet.wait_for(timeout=None)
        def inner():
            runner = crawl_runner(extra_settings=settings)
            items = scrape_items(
                runner, LoginSpider,
                url=url, username=username, password=password,
                extra_js=extra_js)
            d = items.fetch_next
            d.addCallback(lambda result: items.next_item() if result else
                                         {'ok': False, 'error': 'noresult'})
            return d
        result = inner()
        if not result['ok']:
            raise AutoLoginException(result.get('error'))
        return result['cookies']

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
        _, form, meta = forminfo
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
    response = cookie_request(url, cookie_jar)
    filename = '/tmp/autologin_show_in_browser.html'
    with open(filename, 'w+') as f:
        f.write(response.text)
    webbrowser.open(filename, new=2)


def cookie_request(url, cookie_jar):
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': (
            'text/html,application/xhtml+xml,'
            'application/xml;q-0.9,*/*;q=0.8'
        ),
        'Accept-Language': 'en',
    }
    cookies = {c.name: c.value for c in cookie_jar}
    return requests.get(url, headers=headers, cookies=cookies)


def main():
    """
    Command line utility for extracting authenticated login cookies.
    """
    configure_logging()
    argparser = argparse.ArgumentParser(add_help=True)
    argparser.add_argument('username', help='login username')
    argparser.add_argument('password', help='login password')
    argparser.add_argument('url', help='url for the site you wish to login to')
    argparser.add_argument(
        '--splash-url',
        help='URL of the splash instance (by default splash is not used)')
    argparser.add_argument('--http-proxy', help='URL of the http proxy to use')
    argparser.add_argument('--https-proxy', help='URL of the https proxy to use')
    argparser.add_argument(
        '--extra-js', help='path to extra js script executed on login page')
    argparser.add_argument('--show-in-browser', '-b',
        help='show page in browser after login (default: False)',
        action='store_true')
    args = argparser.parse_args()
    # Try logging into site
    auto_login = AutoLogin()
    if args.extra_js:
        with open(args.extra_js, 'rb') as f:
            extra_js = f.read().decode('utf-8')
    else:
        extra_js = None
    settings = {}
    if args.splash_url:
        settings['SPLASH_URL'] = args.splash_url
    if args.http_proxy:
        settings['HTTP_PROXY'] = args.http_proxy
    if args.https_proxy:
        settings['HTTPS_PROXY'] = args.https_proxy
    login_cookies = auto_login.auth_cookies_from_url(
        args.url, args.username, args.password,
        settings=settings, extra_js=extra_js)
    # Print extracted cookies
    pprint.pprint(login_cookies.__dict__)
    # Open browser tab with page using cookies
    if args.show_in_browser:
        show_in_browser(args.url, login_cookies)


if __name__ == '__main__':
    main()
