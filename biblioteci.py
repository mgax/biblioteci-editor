import logging
import flask
from flask.ext.script import Manager
from flask.ext.wtf import Form
from wtforms import TextField
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PropertiesForm(Form):
    name = TextField('name')
    description = TextField('description')


views = flask.Blueprint('views', __name__)


@views.route('/')
def home():
    return flask.render_template('home.html', form=PropertiesForm())


@views.route('/data')
def data():
    data = requests.get(flask.current_app.config['BIBLIOTECI_URL']).content
    return flask.Response(data, content_type='application/json')


def create_app():
    app = flask.Flask(__name__)
    app.config.from_pyfile('settings.py', silent=True)
    app.register_blueprint(views)
    return app


def create_manager(app):
    manager = Manager(app)
    return manager
