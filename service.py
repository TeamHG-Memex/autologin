import os
from flask import Flask
from flask import render_template, Response, request
import json
import hashlib
server_path = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__)
from autologin import AutoLogin
from scrapydutils import ScrapydLoginFinderJob
import hashlib
import time

@app.route("/")
def autologin():
    seed_url = request.args.get("seedurl")
    username = request.args.get("username")
    password = request.args.get("password")

    hash = hashlib.sha1()
    hash.update(str(time.time()))
    db_name = "/tmp/" + hash.hexdigest()[:20] + ".db"
    print "Using DB location %s" % db_name
    
    if not seed_url or not username or not password:
        raise Exception("Missing a needed parameter")

    slfj = ScrapydLoginFinderJob(seed_url, username, password, db_name)
    slfj.schedule()
    slfj.block_until_done()
    
    al = AutoLogin(db_name)
    auth_headers, redirected_to = al.get_auth_headers_and_redirect_url()
    
    return Response(json.dumps({"redirected_to" : redirected_to, "auth_headers" : auth_headers}), mimetype = "application/json")

if __name__ == '__main__':
    app.run(debug = True, threaded = True)