import logging
import flask
from flask.ext.script import Manager
from flask.ext.wtf import Form
from wtforms import TextField, IntegerField
from wtforms.widgets import HiddenInput
import requests
import github

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PropertiesForm(Form):
    id = IntegerField('id', widget=HiddenInput())
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


def update_feature(data):
    document = github.get_data()
    for feature in document['features']:
        properties = feature['properties']
        if properties['id'] == data['id']:
            break
    else:
        raise RuntimeError("Feature not found: %d", data['id'])
    properties.update(data)
    github.commit(document)


@views.route('/save', methods=['POST'])
def save():
    form = PropertiesForm()
    if form.validate_on_submit():
        update_feature(form.data)
        return flask.jsonify(ok=True)
    else:
        return flask.jsonify(ok=False)


def create_app():
    app = flask.Flask(__name__)
    app.config.from_pyfile('settings.py', silent=True)
    app.register_blueprint(views)
    return app


def create_manager(app):
    manager = Manager(app)
    return manager
