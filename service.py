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
from flask import render_template, Response, request, flash, redirect
from forms import LoginForm

server_path = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__)
app.secret_key = 'a334r9asdfmasdfkasdf90joa'

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(
                u"Error in the %s field - %s" % (getattr(form, field).label.text,error),
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
    #sh.rm(sh.glob(os.getcwd() + '/static/browser/*'))
    user_agent = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 ' \
                '(KHTML, like Gecko) Ubuntu Chromium/43.0.2357.130 Chrome/43.0.2357.130 Safari/537.36'
    headers = {
        'User-Agent': user_agent, 
        'Accept': 'text/html,application/xhtml+xml,'
        'application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en',
    }
    # a form of cache busting..kinda
    browser_dir = os.getcwd() + '/static/browser'
    delete_directory_files(browser_dir)

    filename = 'static/browser/{}.html'.format(uuid.uuid4())
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

    f = open(filename, 'w+') 
    f.write(html.tostring(doc))
    f.close()
    return ('ok', filename)

@app.route("/", methods=["GET", "POST"])
def index():
    form = LoginForm(request.form)
    login_cookies = None
    filename = None
    if request.method == 'POST' and form.validate():
        msg = 'Login requested for '
        msg += '{} '.format(form.url.data)
        msg += 'with username={} and '.format(form.username.data)
        msg += 'password={}'.format(form.password.data)
        login_cookies = ['cookie', {'foo': 'bar'}]
        cj = cookielib.CookieJar()
        download = download_page(form.url.data, cj)
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


if __name__ == '__main__':
    app.run(debug = True, threaded = True)
