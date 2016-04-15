from autologin import AutoLogin


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
