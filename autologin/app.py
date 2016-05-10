import os.path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


# Set paths for static assets and temp files
server_path = os.path.dirname(os.path.realpath(__file__))
static_dir = os.path.join(server_path, 'static')
browser_dir = os.path.join(static_dir, 'browser')

# Initiate flask app
app = Flask(__name__)
app.secret_key = 'b334r9asdfmasdfkasdf90joa'
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///' + os.path.join(server_path, 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
