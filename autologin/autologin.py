import sys
import argparse
import re
import urllib2
from urllib import urlencode
from cookielib import CookieJar
from login_form import LoginFormFinder
from urlparse import urlparse
from lxml import html
from lxml.etree import HTMLParser
import webbrowser
import logging


try:
    from formasaurus import FormExtractor
    FORMASAURUS = True
except ImportError:
    FORMASAURUS = False



class AutoLogin():
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
        if FORMASAURUS:
            self.form_extractor = FormExtractor.load()
        else:
            self.form_extractor = None
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
        self.parser = HTMLParser(recover=True, encoding='utf-8')
        self.cookie_jar = CookieJar()

    def logged_in(self, cookies):
        # ToDo...
        for cookie in cookies:
            if 'sessi' in cookie['name']:
                return True
            elif 'sessi' in cookie['value']:
                return True
        return False

    def cookies_to_header(self, cookies):
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie.name] = cookie.value
        headers = {'Cookie': cookie_dict}
        return headers

    def cookies_from_jar(self, cookie_jar):
        cookies = []

        for cookie in cookie_jar:
            cookies.append(cookie.__dict__)

        return cookies

    def login(self, form_url, form_data, referer_url=None):
        cookies = []
        #cj = []

        if referer_url is not None:
            self.headers['Referer'] = referer_url

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
        data = urlencode(form_data)
        print data
        req = urllib2.Request(form_url, data, headers=self.headers)

        try:
            response = opener.open(req, timeout=10)
        except urllib2.URLError as e:
            print(e)
        try:
            cookies = self.cookies_from_jar(cj)
        except:
            print('No cookies found.')
            pass
        
        return self.cookie_jar

    def login_request(self, html_source, username, password, base_url=None, proxy=None):
        request = None
        login_form_finder = LoginFormFinder(
            html_source, username, password, self.form_extractor, base_url)
        args, url, method = login_form_finder.fill_top_login_form()
        print args,url,method

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
        self.cookie_jar = CookieJar()

    def auth_cookies_from_crawl(self, url, username, password, proxy=None):
        # Try to login from any forms on page
        html_source = self.get_html(url)
        login_request = self.login_request(
            html_source, username, password, proxy)

        if login_request:
            return self.auth_cookies_from_html(
                html_source, username, password, proxy)
        else:  # Follow login links and try login
            login_links = self.extract_login_links(html_source)

            for link in login_links:
                html_source = self.get_html(url)
                login_request = self.login_request(username, password, proxy)

                if login_request:
                    return self.auth_cookies_from_html(
                        html_source, username, password, proxy)

            # If we get here, just try all the internal links on the page
            internal_links = self.extract_internal_links(html_source)

            for link in internal_links:
                html_source = self.get_html(url)
                login_request = self.login_request(username, password, proxy)

                if login_request:
                    return self.auth_cookies_from_html(
                        html_source, username, password, proxy)

        return None

    def auth_cookies_from_url(self, url, username, password, proxy=None):
        # Try to login from any forms on page
        html_source = self.get_html(url)
        login_request = self.login_request(
            html_source=html_source,
            username=username,
            password=password,
            base_url=url,
            proxy=proxy
        )

        if login_request:
            return self.auth_cookies_from_html(
                html_source, username, password, proxy)

        return None

    def auth_cookies_from_html(
            self, html_source, username,
            password, base_url=None, proxy=None, referer_url=None):

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
                referer_url)
            return cookies

        return None

    def get_html(self, url):
        html_source = None
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
        req = urllib2.Request(url, headers=self.headers)
        try:
            response = opener.open(req, timeout=10)
            html_source = response.read()
        except urllib2.URLError as e:
            print(e)

        return html_source

    def extract_tokens(self, text):
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
        filename = '/tmp/autologin_show_in_browser.html'
        f = open(filename, 'w+')
        f.write(html_source)
        f.close()
        webbrowser.open(filename, new=2)

    def show_in_browser(self, url, cookie_jar):
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
        req = urllib2.Request(url, headers=self.headers)

        try:
            response = opener.open(req, timeout=10)
        except urllib2.URLError as e:
            print(e)
            sys.exit()

        html_source = response.read()
        filename = '/tmp/autologin_show_in_browser.html'
        f = open(filename, 'w+')
        f.write(html_source)
        f.close()
        webbrowser.open(filename, new=2)


def test_extract_login_links():
    results = []
    found = []
    not_found = []
    total_login_links = 0

    with open('urls.csv') as f:
        auto_login = AutoLogin()
        urls = f.read().splitlines()

        for url in urls:
            print('URL: {}'.format(url))
            html_source = auto_login.get_html(url)
            login_links = auto_login.extract_login_links(html_source)
            results.append([url, login_links])
            total_login_links += len(login_links)

            if len(login_links) > 0:
                found.append(url)
            else:
                not_found.append(url)

    print('#URLs tested: {}'.format(len(results)))
    print('#Total login links: {}'.format(total_login_links))
    print('#URLs with logins: {}'.format(len(found)))
    print('#URLs without logins: {}'.format(len(not_found)))


def test_auth_cookies_from_html():
    url = 'https://reddit.com'
    auto_login = AutoLogin()
    username = 'ghostintheshell1010'
    password = 'B00msh4k3th3r00m!'
    html_source = auto_login.get_html(url)
    auth_cookies = auto_login.auth_cookies_from_html(
        html_source, username, password)
    import webbrowser
    print('Opening browser')
    tmp_response_file = "/tmp/openinbrowser.html"
    f = open(tmp_response_file, "w")
    f.write(auth_headers["response_body"])
    webbrowser.open(tmp_response_file, new=2)


def main(argv):
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
