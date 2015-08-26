import os
from lxml import html
import json
import hashlib
import urllib2
import cookielib
import hashlib
import time
import uuid
import shutil
from autologin import AutoLogin
from flask import Flask
from flask import render_template
from flask import Response
from flask import request
from flask import flash
from flask import redirect
from flask import abort
from flask import jsonify
from forms import LoginForm

server_path = os.path.dirname(os.path.realpath(__file__))
static_dir = os.path.join(server_path, 'static')
browser_dir = os.path.join(static_dir, 'browser')

app = Flask(__name__)
app.secret_key = 'b334r9asdfmasdfkasdf90joa'


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(
                u"Error in the %s field - %s" % (
                    getattr(form, field).label.text, error),
                'danger'
            )


def delete_directory_files(directory_path):
    for file_object in os.listdir(directory_path):
        file_object_path = os.path.join(directory_path, file_object)
        if os.path.isfile(file_object_path):
            os.unlink(file_object_path)
        else:
            shutil.rmtree(file_object_path)


def download_page(url, cookie_jar):
    user_agent = (
            'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Ubuntu Chromium/43.0.2357.130 '
            'Chrome/43.0.2357.130 Safari/537.36'
    )
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,'
        'application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en',
    }
    #browser_dir = os.getcwd() + '/static/browser'
    delete_directory_files(browser_dir)
    filename = '{}.html'.format(uuid.uuid4())
    filepath = os.path.join(browser_dir, filename) 
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
    req = urllib2.Request(url, headers=headers)
    try:
        response = opener.open(req, timeout=10)
    except urllib2.URLError as e:
        return e
    except ValueError as e:
        return ('error', e)
    html_source = response.read()
    doc = html.document_fromstring(html_source)

    f = open(filepath, 'w+')
    f.write(html.tostring(doc))
    f.close()
    return ('ok', filename)


@app.route("/", methods=["GET", "POST"])
def index():
    form = LoginForm(request.form)
    auto_login = AutoLogin()
    login_cookies = None
    filename = None
    if request.method == 'POST' and form.validate():
        msg = 'Login requested for '
        msg += '{} '.format(form.url.data)
        msg += 'with username={} and '.format(form.username.data)
        msg += 'password={}'.format(form.password.data)
        login_cookie_jar = auto_login.auth_cookies_from_url(
            url=form.url.data,
            username=form.username.data,
            password=form.password.data
        )
        download = download_page(form.url.data, login_cookie_jar)
        login_cookies = login_cookie_jar.__dict__
        if download[0] != 'ok':
            flash(download, 'danger')
        else:
            flash(msg, 'success')
            filename = download[1]
    else:
        flash_errors(form)
    return render_template(
        'index.html',
        form=form,
        login_cookies=login_cookies,
        filename=filename
    )


@app.route("/login-cookies", methods=["POST"])
def get_login_cookies():

    if not request.json:
        abort(400)
    if 'url' not in request.json:
        abort(400)
    if 'username' not in request.json:
        abort(400)
    if 'password' not in request.json:
        abort(400)

    auto_login = AutoLogin()
    login_cookie_jar = auto_login.auth_cookies_from_url(
        url=request.json['url'],
        username=request.json['username'],
        password=request.json['password']
    )
    login_cookies = auto_login.cookies_from_jar(login_cookie_jar)

    return jsonify({'cookies': login_cookies}), 201


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
