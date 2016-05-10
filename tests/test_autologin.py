import pytest

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
def test_auth_cookies_from_url_login1():
    al = AutoLogin()
    url = 'http://localhost:{}/login1'.format(PORT)
    with MockServer():
        # no login form
        with pytest.raises(AutoLoginException) as e:
            al.auth_cookies_from_url(url + '?hide=', 'admin', 'secret')
        assert e.value.args[0] == 'nologinform'
        # wrong password
        with pytest.raises(AutoLoginException) as e:
            al.auth_cookies_from_url(url, 'admin', 'wrong')
        assert e.value.args[0] == 'badauth'
        # normal auth
        cookies = al.auth_cookies_from_url(url + '?foo=', 'admin', 'secret')
        assert {c.name: c.value for c in cookies} == {'_auth': 'yes'}
        # redirect to the same URL
        cookies = al.auth_cookies_from_url(url, 'admin', 'secret')
        assert {c.name: c.value for c in cookies} == {'_auth': 'yes'}


@pytest.mark.last
def test_auth_cookies_from_url_login2():
    al = AutoLogin()
    url = 'http://localhost:{}/login2'.format(PORT)
   #with MockServer():
   #    # wrong password
   #    with pytest.raises(AutoLoginException) as e:
   #        al.auth_cookies_from_url(url + '?foo=', 'admin', 'wrong')
   #    assert e.value.args[0] == 'badauth'
    with MockServer():
        # normal auth
        cookies = al.auth_cookies_from_url(url, 'admin', 'secret')
        assert {c.name: c.value for c in cookies} == {'session': '1'}
