import flask
from flask.ext.script import Manager
import requests

BIBLIOTECI_URL = ('https://raw2.github.com/mgax/biblioteci/'
                  'master/biblioteci.geojson')

views = flask.Blueprint('views', __name__)


@views.route('/')
def home():
    return flask.render_template('home.html')


@views.route('/data')
def data():
    data = requests.get(BIBLIOTECI_URL).content
    return flask.Response(data, content_type='application/json')


def create_app():
    app = flask.Flask(__name__)
    app.register_blueprint(views)
    return app


def create_manager(app):
    manager = Manager(app)
    return manager
