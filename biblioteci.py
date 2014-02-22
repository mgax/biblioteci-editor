import logging
import flask
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security, UserMixin, RoleMixin, login_required
from flask.ext.security.datastore import SQLAlchemyUserDatastore
from flask.ext.social import Social
from flask.ext.social.datastore import SQLAlchemyConnectionDatastore
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

db = SQLAlchemy()


roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Text, unique=True)
    description = db.Column(db.Text)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, unique=True)
    active = db.Column(db.Boolean)
    confirmed_at = db.Column(db.DateTime)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))


class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    provider_id = db.Column(db.Text)
    provider_user_id = db.Column(db.Text)
    access_token = db.Column(db.Text)
    secret = db.Column(db.Text)
    display_name = db.Column(db.Text)
    profile_url = db.Column(db.Text)
    image_url = db.Column(db.Text)
    rank = db.Column(db.Integer)

    user = db.relationship('User')


class ConnectionDatastore(SQLAlchemyConnectionDatastore):

    def find_connection(self, **kwargs):
        connection = super(ConnectionDatastore, self).find_connection(**kwargs)

        if connection is None:
            connection = Connection(user=User(active=True), **kwargs)
            db.session.add(connection)
            db.session.commit()
            logging.info("Created new user: %r %r", connection.user.id, kwargs)

        return connection


views = flask.Blueprint('views', __name__)


@views.route('/')
def home():
    return flask.render_template('home.html')


@views.route('/authenticate')
def login():
    return flask.render_template('login.html')


@views.route('/profile')
@login_required
def profile():
    providers = flask.current_app.extensions['social']
    return flask.render_template('profile.html', **{
        'content': 'Profile Page',
        'google_conn': providers.google.get_connection(),
    })


@views.route('/data')
def data():
    data = requests.get(flask.current_app.config['BIBLIOTECI_URL']).content
    return flask.Response(data, content_type='application/json')


def create_app():
    app = flask.Flask(__name__)
    app.config.from_pyfile('settings.py', silent=True)
    app.config.update({'SECURITY_POST_LOGIN': '/profile'})
    db.init_app(app)
    Security(app, SQLAlchemyUserDatastore(db, User, Role))
    Social(app, ConnectionDatastore(db, Connection))
    app.login_manager.login_view = "views.login"
    app.register_blueprint(views)
    return app


def create_manager(app):
    manager = Manager(app)
    return manager
