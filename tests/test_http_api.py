import json
import six

import pytest
from twisted.trial import unittest
from twisted.internet.defer import inlineCallbacks
from twisted.web import server
from twisted.internet.defer import succeed
from twisted.web.test.test_web import DummyRequest

from tests.mockserver import MockServer, PORT, Login
from autologin.http_api import AutologinAPI


class WebTest(unittest.TestCase):
    @inlineCallbacks
    def test_login1(self):
        url = 'http://localhost:{}{}'.format(PORT, Login.url)
        view = AutologinAPI()
        with MockServer():
            request = api_request(url=url, username='admin', password='secret')
            yield render(view, request)
            result = api_result(request)
            assert result['status'] == 'solved'
            assert result['start_url'] == url
            assert {c['name']: c['value'] for c in result['cookies']} == \
                   {'_auth': 'yes'}
            assert 'response' in result
            response = result['response']
            assert response['cookies'] == result['cookies']
            assert 'text' in response
            assert 'headers' in response

    @inlineCallbacks
    def test_login_wrong_pw(self):
        url = 'http://localhost:{}{}'.format(PORT, Login.url)
        view = AutologinAPI()
        with MockServer():
            request = api_request(url=url, username='admin', password='wrong')
            yield render(view, request)
            result = api_result(request)
            assert result['status'] == 'error'
            assert 'response' in result
            response = result['response']
            assert 'cookies' in response
            assert 'text' in response
            assert 'headers' in response

    @inlineCallbacks
    def test_errors(self):
        view = AutologinAPI()
        with MockServer():
            request = api_request(username='admin', password='secret')
            with pytest.raises(HttpError) as excinfo:
                yield render(view, request)
            assert excinfo.value.args[0] == 'Missing required field "url"'

            request = api_request(url='http://example.com', foo='bar')
            with pytest.raises(HttpError) as excinfo:
                yield render(view, request)
            assert excinfo.value.args[0] == 'Arguments foo not supported'


def api_request(**kwargs):
    request = DummyRequest([''])
    request.method = b'POST'
    request.content = six.BytesIO(json.dumps(kwargs).encode('utf-8'))
    return request


def api_result(request):
    return json.loads(b''.join(request.written).decode('utf-8'))


class HttpError(Exception):
    pass


def render(resource, request):
    result = resource.render(request)
    if isinstance(result, str) and request.responseCode == 200:
        request.write(result)
        request.finish()
        return succeed(None)
    elif result is server.NOT_DONE_YET:
        if request.finished:
            return succeed(None)
        else:
            return request.notifyFinish()
    else:
        raise HttpError(result.decode('utf-8'))
