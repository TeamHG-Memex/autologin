from six.moves import configparser
import os.path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


# Set paths for static assets and temp files
server_path = os.path.dirname(os.path.realpath(__file__))
static_dir = os.path.join(server_path, 'static')
browser_dir = os.path.join(static_dir, 'browser')


def init_app():
    # Read config (defaults are in autologin.conf)
    config = configparser.ConfigParser()
    # Read default config
    default_config = os.path.join(server_path, 'autologin.cfg')
    config.read(default_config)
    # Override by user-supplied config
    custom_configs = config.read([
        os.path.expanduser('~/.autologin.cfg'),
        '/etc/autologin.cfg',
        ])

    # Initiate flask app
    app = Flask(__name__)
    app.secret_key = config.get('autologin', 'secret_key')
    try:
        db_path = config.get('autologin', 'db')
    except configparser.NoOptionError:
        db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite')
    else:
        if not os.path.isabs(db_path) and custom_configs:
            where = custom_configs[0] if len(custom_configs) == 1 else \
                    'one of {}'.format(', '.join(custom_configs))
            raise RuntimeError(
                'You must specify an absolute path to the database. '
                'Invalid relative path "{db_path}" in {where}'
                .format(db_path=db_path, where=where))
    assert os.path.isabs(db_path), 'Absolute path expected'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(db_path)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app


def init_db():
    import logging
    logger = logging.getLogger(__name__)
    logger.info('Keychain UI database: %s'
                % app.config['SQLALCHEMY_DATABASE_URI'])
    db.create_all()


app = init_app()
db = SQLAlchemy(app)
