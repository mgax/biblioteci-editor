import flask
from flask.ext.script import Manager

views = flask.Blueprint('views', __name__)


@views.route('/')
def home():
    return 'hi'


def create_app():
    app = flask.Flask(__name__)
    app.register_blueprint(views)
    return app


def create_manager(app):
    manager = Manager(app)
    return manager
