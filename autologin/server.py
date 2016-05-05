from __future__ import absolute_import
import os
import uuid
import shutil

from lxml import html
from flask import render_template
from flask import flash
import flask_admin
import requests

from .autologin import AutoLogin
from .forms import LoginForm
from .app import app, db, server_path
from .login_keychain import KeychainItemAdmin, KeychainItem
from .autologin import cookie_request, AutoLoginException


def flash_errors(form):
    """
    Method for displaying flash messages with form errors.
    Pass the form as a parameter.
    """
    for field, errors in form.errors.items():
        for error in errors:
            flash(
                u"Error in the %s field - %s" % (
                    getattr(form, field).label.text, error),
                'danger'
            )


def delete_directory_files(directory_path):
    """
    Method for deleting temporary html files created by
    show in browser process.
    """
    for filename in os.listdir(directory_path):
        if filename != 'README':
            path = os.path.join(directory_path, filename)
            if os.path.isfile(path):
                os.unlink(path)
            else:
                shutil.rmtree(path)


def download_page(url, cookie_jar):
    """
    Request page using authenticated cookies (cookiejar).
    Download html source and save in browser directory, to
    be used by in show_in_browser().
    """
    browser_dir = os.path.join(server_path, 'static/browser')
    delete_directory_files(browser_dir)
    filename = '{}.html'.format(uuid.uuid4())
    filepath = os.path.join(browser_dir, filename)
    try:
        response = cookie_request(url, cookie_jar)
    except requests.RequestException as e:
        return e, None
    doc = html.document_fromstring(response.text)
    with open(filepath, 'wb') as f:
        f.write(html.tostring(doc))
    return None, filename


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main app route.
    Hosts form used for testing autologin.
    User can submit credentials and URL,
    authenticated cookies returned.
    Also makes a request using extracted cookies,
    saves the source and allows you to view in browser.
    Useful for checking whether login was successful.
    """
    from flask import request
    form = LoginForm(request.form)
    auto_login = AutoLogin()
    login_cookies = None
    login_links = None
    filename = None
    # Process form submission
    if request.method == 'POST' and form.validate():
        url = form.url.data
        username = form.username.data
        password = form.password.data
        msg = ('Login requested for {url} with username={username} '
               'and password={password}'.format(
                   url=url, username=username, password=password))
        # Attempt login
        try:
            login_cookie_jar = auto_login.auth_cookies_from_url(
                url, username, password)
        except AutoLoginException as e:
            flash(e, 'danger')
        else:
            # If we've extracted some cookies,
            # use them to request a page and download html source
            # for viewing in browser,
            login_cookies = login_cookie_jar.__dict__
            error, filename = download_page(form.url.data, login_cookie_jar)
            if error:
                flash(error, 'danger')
            else:
                flash(msg, 'success')
    else:
        flash_errors(form)
    return render_template(
        'index.html',
        form=form,
        login_cookies=login_cookies,
        login_links=login_links,
        filename=filename
    )


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8088)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    db.create_all()
    admin = flask_admin.Admin(app, template_mode='bootstrap3')
    admin.add_view(KeychainItemAdmin(KeychainItem, db.session))

    app.run(args.host, args.port, debug=args.debug, threaded=True)
