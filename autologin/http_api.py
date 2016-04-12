from __future__ import absolute_import
import json

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource

from .app import app, db
from .login_keychain import KeychainItem
from .spiders import FormSpider, LoginSpider, crawl_runner
from .scrapyutils import scrape_items


def return_json(dct):
    returnValue(json.dumps(dct).encode('utf-8'))


class Index(Resource):
    isLeaf = True

    def render_GET(self, _request):
        return b'API: POST /login-cookies {"url": url}'


class AutologinAPI(Resource):
    isLeaf = True

    def render_POST(self, request):
        try:
            data = json.loads(request.content.read().decode('utf-8'))
        except (TypeError, ValueError):
            request.setResponseCode(400)
            return b'JSON body expected'
        url = data.get('url')
        if url is None:
            request.setResponseCode(400)
            return b'Missing required field "url"'

        self._render_POST(request, data)
        return NOT_DONE_YET

    @inlineCallbacks
    def _render_POST(self, request, data):
        result = yield self._handle_request(
            data['url'],
            username=data.get('username'),
            password=data.get('password'),
            splash_url=data.get('splash_url'),
            settings=data.get('settings'),
        )

        if not isinstance(result, bytes):
            result = result.encode('utf8')

        request.write(result)

        if not request.finished:
            request.finish()

    @inlineCallbacks
    def _handle_request(self, url,
                        username=None, password=None, splash_url=None,
                        settings=None):
        runner = crawl_runner(splash_url=splash_url, extra_settings=settings)
        if username is None and password is None:
            with app.app_context():
                credentials = KeychainItem.get_credentials(url)

                if not credentials:
                    credentials = KeychainItem.add_task(url)
                    if credentials:
                        runner.crawl(FormSpider, url, credentials)
                    return_json({'status': 'pending'})
                elif credentials.skip:
                    return_json({'status': 'skipped'})
                elif not credentials.solved:
                    return_json({'status': 'pending'})
                else:
                    login_url = credentials.login_url
                    username = credentials.login
                    password = credentials.password
        else:
            login_url = url

        item = yield self._login(runner, login_url, username, password)
        if item is None:
            return_json({'status': 'error', 'error': 'unknown'})
        elif not item['ok']:
            return_json({'status': 'error', 'error': item['error']})

        return_json({
            'status': 'solved',
            'cookies': item['cookies'],
            'start_url': item['start_url']
        })

    @inlineCallbacks
    def _login(self, runner, login_url, username, password):
        async_items = scrape_items(runner,
                                   LoginSpider,
                                   url=login_url,
                                   username=username,
                                   password=password)
        while (yield async_items.fetch_next):
            returnValue(async_items.next_item())


root = Resource()
root.putChild(b'', Index())
root.putChild(b'login-cookies', AutologinAPI())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8089)
    args = parser.parse_args()
    db.create_all()
    print("Autologin HTTP API is started on port %s" % args.port)
    reactor.listenTCP(args.port, Site(root))
    reactor.run()
