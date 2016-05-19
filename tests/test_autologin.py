import pytest
import unittest

from autologin import AutoLogin, AutoLoginException
from tests.mockserver import MockServer, PORT


def test_login_request():
    al = AutoLogin()
    html = '''
    <form method="POST" action=".">
        <input type="email" name="login">
        <input type="password" name="password">
        <input type="submit" value="Login">
    </form>
    '''
    req = al.login_request(html, username='admin', password='secret')
    assert req == {
        'body': 'login=admin&password=secret',
        'headers': {b'Content-Type': b'application/x-www-form-urlencoded'},
        'method': 'POST',
        'url': '.'}
    req = al.login_request(html, username='admin', password='secret',
                           base_url='/login/')
    assert req == {
        'body': 'login=admin&password=secret',
        'headers': {b'Content-Type': b'application/x-www-form-urlencoded'},
        'method': 'POST',
        'url': '/login/'}


# These tests should be run last as it uses crochet, and normal scrapy spider
# is not finalized correctly after a call to crochet.setup.
@pytest.mark.last
class TestAuthCookiesFromUrl(unittest.TestCase):
    
    url = 'http://127.0.0.1:{}/login1'.format(PORT)
    url_no_change_cookie = 'http://127.0.0.1:{}/login2'.format(PORT)

    def setUp(self):
        self.al = AutoLogin()
        self.mockserver = MockServer()
        self.mockserver.__enter__()

    def tearDown(self):
        self.mockserver.__exit__(None, None, None)

    def test_no_login_form(self):
        with pytest.raises(AutoLoginException) as e:
            self.al.auth_cookies_from_url(
                self.url + '?hide=', 'admin', 'secret')
        assert e.value.args[0] == 'nologinform'

    def test_wrong_password(self):
        with pytest.raises(AutoLoginException) as e:
            self.al.auth_cookies_from_url(self.url, 'admin', 'wrong')
        assert e.value.args[0] == 'badauth'

    def test_normal_auth(self):
        cookies = self.al.auth_cookies_from_url(
            self.url + '?foo=', 'admin', 'secret')
        assert {c.name: c.value for c in cookies} == {'_auth': 'yes'}

    def test_redirect_to_same_url(self):
        cookies = self.al.auth_cookies_from_url(self.url, 'admin', 'secret')
        assert {c.name: c.value for c in cookies} == {'_auth': 'yes'}

    def test_proxy(self):
        assert 'localhost' not in self.url, 'proxy_bypass bypasses localhost'
        cookies = self.al.auth_cookies_from_url(
            self.url, 'admin', 'secret',
            settings={'HTTP_PROXY': 'http://127.0.0.1:8123'},
        )
        assert {c.name: c.value for c in cookies} == {'_auth': 'yes'}

    def test_no_change_cookie(self):
        cookies = self.al.auth_cookies_from_url(
            self.url_no_change_cookie, 'admin', 'secret')
        assert {c.name: c.value for c in cookies} == {'session': '1'}

    def test_no_change_cookie_wrong_password(self):
        with pytest.raises(AutoLoginException) as e:
            self.al.auth_cookies_from_url(
                self.url_no_change_cookie, 'admin', 'wrong')
        assert e.value.args[0] == 'badauth'
