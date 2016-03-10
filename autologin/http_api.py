import json

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.resource import Resource

from .autologin import AutoLogin
from .app import db


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
        for field in ['url', 'username', 'password']:
            if field not in data:
                request.setResponseCode(400)
                return 'Missing required field "%s"' % field

        auto_login = AutoLogin()
        login_cookie_jar = auto_login.auth_cookies_from_url(
            url=data['url'],
            username=data['username'],
            password=data['password'],
        )
        if login_cookie_jar is not None:
            login_cookies = auto_login.cookies_from_jar(login_cookie_jar)
        else:
            login_cookies = {}

        request.setResponseCode(201)
        return json.dumps({'cookies': login_cookies})


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
