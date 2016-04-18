import json
import six

from twisted.trial import unittest
from twisted.internet.defer import inlineCallbacks
from twisted.web import server
from twisted.internet.defer import succeed
from twisted.web.test.test_web import DummyRequest

from tests.mockserver import MockServer, PORT
from autologin.http_api import AutologinAPI


class WebTest(unittest.TestCase):
    @inlineCallbacks
    def test(self):
        url = 'http://localhost:{}'.format(PORT)
        view = AutologinAPI()
        with MockServer():
            request = api_request(
                url=url + '?foo=', username='admin', password='secret')
            yield render(view, request)
            result = api_result(request)
            assert result['status'] == 'solved'
            assert result['start_url'] == 'http://localhost:8781/'
            assert {c['name']: c['value'] for c in result['cookies']} == \
                   {'_auth': 'yes'}


def api_request(**kwargs):
    request = DummyRequest([''])
    request.method = b'POST'
    request.content = six.BytesIO(
        json.dumps(kwargs).encode('utf-8'))
    return request


def api_result(request):
    return json.loads(b''.join(request.written).decode('utf-8'))


def render(resource, request):
    result = resource.render(request)
    if isinstance(result, str):
        request.write(result)
        request.finish()
        return succeed(None)
    elif result is server.NOT_DONE_YET:
        if request.finished:
            return succeed(None)
        else:
            return request.notifyFinish()
    else:
        raise ValueError('Unexpected return value: %r' % (result,))
