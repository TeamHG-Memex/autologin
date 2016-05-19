from six.moves import configparser
import os.path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


# Set paths for static assets and temp files
server_path = os.path.dirname(os.path.realpath(__file__))
static_dir = os.path.join(server_path, 'static')
browser_dir = os.path.join(static_dir, 'browser')

# Read config (defaults are in autologin.conf)
config = configparser.ConfigParser()
# Read default config
config.read(os.path.join(server_path, 'autologin.cfg'))
# Override by user-supplied config
config.read([
    os.path.expanduser('~/.autologin.cfg'),
    '/etc/autologin.cfg',
    ])

# Initiate flask app
app = Flask(__name__)
app.secret_key = config.get('autologin', 'secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(os.path.abspath(
    os.path.join(config.get('autologin', 'db_folder'), 'db.sqlite')))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
