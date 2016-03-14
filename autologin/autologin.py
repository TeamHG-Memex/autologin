#!/usr/bin/env python
from __future__ import print_function
import sys
import argparse
import re
import ssl
import urllib2
from urllib import urlencode
from cookielib import CookieJar
from login_form import LoginFormFinder, NotFoundError
from urlparse import urlparse
from lxml import html
from lxml.etree import HTMLParser
import webbrowser
import logging
from traceback import print_exc

# Use formasaurus for form identification.
# There is a fallback if it is not installed.
# However, formasaurus is more effecive at finding login forms.
# https://github.com/TeamHG-Memex/Formasaurus
try:
    from formasaurus import FormExtractor
    FORMASAURUS = True
except ImportError:
    FORMASAURUS = False



class AutoLogin():
    # Keywords used to pattern match login links
    # Both anchor href and text are checked.
    login_keywords = [
        'login',
        'logon',
        'myaccount',
        'signin',
        'sign in',
        'log in',
        'login / join',
        'login / register'
    ]

    def __init__(self):
        # Use naive scoring algorithm if formasuarus is not installed
        if FORMASAURUS:
            self.form_extractor = FormExtractor.load()
        else:
            self.form_extractor = None
        # Set some friendly headers
        self.user_agent = (
            'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Ubuntu Chromium/43.0.2357.130 '
            'Chrome/43.0.2357.130 Safari/537.36'
        )
        self.accept_encoding = (
            'text/html,application/xhtml+xml,'
            'application/xml;q-0.9,*/*;q=0.8'
        )
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': self.accept_encoding,
            'Accept-Language': 'en',
        }
        # Cookie jar and html parser for making requests with urllib
        self.parser = HTMLParser(recover=True, encoding='utf-8')
        self.cookie_jar = CookieJar()


    def encode_var(self, var):
        """
        Method for encoding a form variable. 
        UTF-8 instead of unicode.
        """
        if isinstance(var, unicode):
            return var.encode('utf-8')
        else:
            return str(var)
            
    def encode_form_dict(self, form_data):
        """
        Method to encode all form variables as UTF-8.
        Returns a dictionary.
        """
        encoded_dict = {} 
        for field,value in form_data.items():
            field = self.encode_var(field)
            value = self.encode_var(value)
            encoded_dict[field] =  value
        return encoded_dict

    def logged_in(self, cookies):
        """
        Method to determine whether a request is authenticated.
        Not yet implemented.
        """
        # ToDo...
        for cookie in cookies:
            if 'sessi' in cookie['name']:
                return True
            elif 'sessi' in cookie['value']:
                return True
        return False

    def cookies_to_header(self, cookies):
        """
        Turn a cookie a cookie jar into a header.
        If you do not want to use a cookie jar,
        you can send the authenticated cookies as a header.
        Returns a dictionary.
        """
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie.name] = cookie.value
        headers = {'Cookie': cookie_dict}
        return headers

    def cookies_from_jar(self, cookie_jar):
        """
        Extract cookie jar into a list of cookies.
        Some of the values are objects, so this requires further work.
        """
        # ToDo - translate nested cookiejar/urllib objects
        cookies = []

        for cookie in cookie_jar:
            cookies.append(cookie.__dict__)

        return cookies

    def login(self, form_url, form_data, base_url=None):
        """
        Attempt to login to a site using form_data dictionary.
        Uses a cookielib cookiejar https://docs.python.org/2/library/cookielib.html.
        Request timeout is set to 10 seconds.
        Returns the cookiejar.
        """
        self.headers['Referer'] = base_url
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
        encoded_form_data = self.encode_form_dict(form_data)
        data = urlencode(encoded_form_data)
        req = urllib2.Request(form_url, data, headers=self.headers)

        try:
            response = opener.open(req, timeout=10)
        except (urllib2.URLError, ssl.SSLError) as e:
            print('Error while submiting a form to %s' % form_url,
                  file=sys.stderr)
            print_exc()
        try:
            cookies = self.cookies_from_jar(self.cookie_jar)
        except:
            print('No cookies found.', file=sys.stderr)
        return self.cookie_jar

    def login_request(self, html_source, username, password, base_url=None, proxy=None):
        """
        Search html_source for login forms, return a form request dictionary.
        The request dictionary contains the form action URL and the data to post.
        """
        request = None
        try:
            login_form_finder = LoginFormFinder(
                html_source, username, password, self.form_extractor, base_url)
            args, url, method = login_form_finder.fill_top_login_form()
        except NotFoundError:
            return None

        if args is not None and url is not None:
            data = {}
            for arg in args:
                data[arg[0]] = arg[1]

            request = {
                'url': url,
                'method': method,
                'data': data,
            }

        return request

    def reset_cookies(self):
        """
        Cookies are stored as a class attribute.
        If using an object across multiple login attempts,
        you may want to reset the cookies.
        """
        self.cookie_jar = CookieJar()

    #def auth_cookies_from_crawl(self, url, username, password, proxy=None):
    #    # Try to login from any forms on page
    #    html_source = self.get_html(url)
    #    login_request = self.login_request(
    #        html_source, username, password, proxy)

    #    if login_request:
    #        return self.auth_cookies_from_html(
    #            html_source, username, password, proxy)
    #    else:  # Follow login links and try login
    #        login_links = self.extract_login_links(html_source)

    #        for link in login_links:
    #            html_source = self.get_html(url)
    #            login_request = self.login_request(username, password, proxy)

    #            if login_request:
    #                return self.auth_cookies_from_html(
    #                    html_source, username, password, proxy)

    #        # If we get here, just try all the internal links on the page
    #        internal_links = self.extract_internal_links(html_source)

    #        for link in internal_links:
    #            html_source = self.get_html(url)
    #            login_request = self.login_request(username, password, proxy)

    #            if login_request:
    #                return self.auth_cookies_from_html(
    #                    html_source, username, password, proxy)

    #    return None

    def auth_cookies_from_url(self, url, username, password, proxy=None):
        """
        Attempt to login and return the authenticated cookies.
        """
        # Try to login from any forms on page
        html_source = self.get_html(url)
        if html_source:
            login_request = self.login_request(
                html_source=html_source,
                username=username,
                password=password,
                base_url=url,
                proxy=proxy,
            )

            if login_request is not None:
                cookies = self.login(
                    form_url=login_request['url'],
                    form_data=login_request['data'],
                    base_url=login_request['url'])
                return cookies

        return None

    def auth_cookies_from_html(
            self, html_source, username,
            password, base_url=None, proxy=None):
            #password, base_url=None, proxy=None, referer_url=None):

        cookies = []
        login_request = self.login_request(
                    html_source=html_source,
                    username=username,
                    password=password,
                    base_url=base_url
                )

        if login_request is not None:
            cookies = self.login(
                login_request['url'],
                login_request['data'],
                base_url)
                #referer_url)
            return cookies

        return None

    def get_html(self, url):
        """
        Method to return the html source of a page.
        Uses the object cookie jar, allowing you to request the login page,
        find the login form, then submit a login request while persistiing the cookies.
        Some sites require this flow for authentication.
        """
        html_source = None
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
        req = urllib2.Request(url, headers=self.headers)
        try:
            response = opener.open(req, timeout=10)
            html_source = response.read()
        except (urllib2.URLError, ssl.SSLError) as e:
            print('Error while getting html at %s' % url, file=sys.stderr)
            print_exc()

        return html_source

    def extract_tokens(self, text):
        """
        Tokenize a string, replacing nonalphanumeric characters.
        Used to match against login keywords.
        """
        # Split by non-alphanumeric characters
        keyword_list = re.findall(r'\w+', text)
        # Create sanitized list,
        # ignoring digits and any remaining irrelevant characters
        sanitized_list = []

        for keyword in keyword_list:
            if not keyword.isdigit():
                keyword = keyword.replace('_', ' ')
                keyword = keyword.replace('-', ' ')
                keyword = keyword.strip()
                sanitized_list.append(keyword)

        return sanitized_list

    def is_login_link(self, link_element):
        """
        Take an lxml link element and test whether it is a login link.
        Tokenezise the items in the href and text and checks whether they
        match login keywords.
        """
        # Tokenize href
        href = link_element.xpath('@href')[0]
        href_tokens = self.extract_tokens(href)

        # Tokenize link text
        # Handle cases where there is no text, e.g. image
        try:
            text = link_element.xpath('text()')[0].lower().strip()
        except:
            text = ''

        # Combine into single token list
        tokens = href_tokens + [text]
        # Check whether tokens match any login keywords
        matches = set(tokens) & set(self.login_keywords)

        if len(matches) > 0:
            return True

        return False

    def extract_login_links(self, html_source, regex_filter=None):
        """
        Extract login links from html source.
        """
        results = []
        doc = html.document_fromstring(html_source, self.parser)
        links = doc.xpath('//a')
        print('#Links: {}'.format(len(links)))

        for link in links:
            # Ignore links without href
            try:
                href = link.xpath('@href')[0]
            except:
                continue

            is_login = self.is_login_link(link)

            if is_login and link not in results:
                results.append(href)

        print('#Login links: {}'.format(len(results)))
        return results

    def show_html_in_browser(self, html_source):
        """
        Save html in /tmp/ directory, then open using webbrowser.
        Used for testing.
        """
        filename = '/tmp/autologin_show_in_browser.html'
        f = open(filename, 'w+')
        f.write(html_source)
        f.close()
        webbrowser.open(filename, new=2)

    def show_in_browser(self, url, cookie_jar):
        """
        Get html source, save in /tmp/ directory,
        then show in browser using webbrowser.
        """
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
        req = urllib2.Request(url, headers=self.headers)

        try:
            response = opener.open(req, timeout=10)
        except urllib2.URLError as e:
            print_exc()
            sys.exit()

        html_source = response.read()
        filename = '/tmp/autologin_show_in_browser.html'
        f = open(filename, 'w+')
        f.write(html_source)
        f.close()
        webbrowser.open(filename, new=2)



def main(argv):
    """
    Command line utility for extracting authenticated login cookies.
    Params: username, password, url.
    Proxy support not yet implemented.
    """
    import pprint
    if not FORMASAURUS:
        logging.warning('Formasaurus is not installed. Install it here: https://github.com/TeamHG-Memex/Formasaurus. AutoLogin will still work, it will just be a little less successful.')
    show_in_browser = None
    argparser = argparse.ArgumentParser(add_help=True)
    argparser.add_argument(
        'username',
        help=('login username'),
        type=str
    )
    argparser.add_argument(
        'password',
        help=('login password'),
        type=str
    )
    argparser.add_argument(
        'url',
        help=(
            'url for the site you wish to login to'
        ),
        type=str
    )
    argparser.add_argument(
        '--proxy',
        '-p',
        help=('proxy in format protocol://username:password:ipaddress:host'),
        type=int,
    )
    argparser.add_argument(
        '--show-in-browser',
        '-b',
        help=('show page in browser after login (default: False)'),
        type=bool,
        default=False
    )
    # Parse command line input
    args = argparser.parse_args()
    # Try logging into site
    auto_login = AutoLogin()
    login_cookies = auto_login.auth_cookies_from_url(
        args.url, args.username, args.password)
    # Print extracted cookies
    pprint.pprint(login_cookies.__dict__)

    # Open browser tab with page using cookies
    if args.show_in_browser:
        auto_login.show_in_browser(args.url, login_cookies)


if __name__ == '__main__':
    main(sys.argv)
