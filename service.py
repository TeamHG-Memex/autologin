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
import webbrowser

@app.route("/")
def autologin():
    seed_url = request.args.get("seedurl")
    username = request.args.get("username")
    password = request.args.get("password")
    use_formasaurus = request.args.get("formasaurus")
    open_in_browser = request.args.get("openinbrowser")

    hash = hashlib.sha1()
    hash.update(str(time.time()))
    db_name = "/tmp/" + hash.hexdigest()[:20] + ".db"
    
    if not seed_url or not username or not password:
        raise Exception("Missing a needed parameter")

    if use_formasaurus == "0":
        use_formasaurus = False
    else:
        use_formasaurus = True 

    slfj = ScrapydLoginFinderJob(seed_url, username, password, db_name, use_formasaurus=use_formasaurus)
    slfj.schedule()
    slfj.block_until_done()
    
    al = AutoLogin(db_name)
    auth_info = al.get_auth_info()
    print 'Waaaaaaaaa? %s'  % open_in_browser

    if open_in_browser == "1":
        print 'Opening browser'
        tmp_response_file = "/tmp/openinbrowser.html" 
        f = open(tmp_response_file, "w")
        f.write(auth_info["response_body"].encode("utf-8"))
        webbrowser.open(tmp_response_file, new = 2)
    
    return Response(json.dumps(auth_info), mimetype = "application/json")

if __name__ == '__main__':
    app.run(debug = True, threaded = True)
