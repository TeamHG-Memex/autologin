from __future__ import absolute_import
import json

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.resource import Resource

from .autologin import AutoLogin
from .app import app, db
from .login_keychain import KeychainItem
from .spider import Spider, crawl_runner


class Index(Resource):
    isLeaf = True

    def render_GET(self, _request):
        return 'API: POST /login-cookies {"url": url}'


class AutologinAPI(Resource):
    isLeaf = True

    def render_POST(self, request):
        try:
            data = json.loads(request.content.read())
        except (TypeError, ValueError):
            request.setResponseCode(400)
            return 'JSON body expected'
        url = data.get('url')
        if url is None:
            request.setResponseCode(400)
            return 'Missing required field "url"'
        with app.app_context():
            return self._handle_request(
                url,
                username=data.get('username'),
                password=data.get('password'))

    def _handle_request(self, url, username=None, password=None):
        # TODO - restore old API (explicit username and password)
        # TODO - and maybe make it use the crawler too?
        credentials = KeychainItem.get_credentials(url)
        if not credentials:
            item = KeychainItem.add_task(url)
            if item:
                crawl_runner.crawl(Spider, url, item)
            return json.dumps({'status': 'pending'})
        elif credentials.skip:
            return json.dumps({'status': 'skipped'})
        elif not credentials.solved:
            return json.dumps({'status': 'pending'})
        else:
            auto_login = AutoLogin()
            login_cookie_jar = auto_login.auth_cookies_from_url(
                url=credentials.login_url,
                username=credentials.login,
                password=credentials.password,
            )
            if login_cookie_jar is not None:
                login_cookies = auto_login.cookies_from_jar(login_cookie_jar)
            else:
                login_cookies = {}
            return json.dumps({'status': 'solved', 'cookies': login_cookies})


root = Resource()
root.putChild('', Index())
root.putChild('login-cookies', AutologinAPI())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8089)
    args = parser.parse_args()
    db.create_all()
    reactor.listenTCP(args.port, Site(root))
    reactor.run()
