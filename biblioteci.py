import logging
import flask
from flask.ext.script import Manager
from flask.ext.wtf import Form
from flask.ext.oauthlib.client import OAuth
from werkzeug.contrib.cache import SimpleCache
from wtforms import TextField, IntegerField
from wtforms.widgets import HiddenInput, TextArea
import requests
import github

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cache = SimpleCache()


class PropertiesForm(Form):
    id = IntegerField('id', widget=HiddenInput())
    name = TextField('name')
    description = TextField('description', widget=TextArea())
    address = TextField('address')
    locality = TextField('locality')
    website_url = TextField('website_url')
    catalog_url = TextField('catalog_url')
    facebook_url = TextField('facebook_url')
    open_hours = TextField('open_hours')


views = flask.Blueprint('views', __name__)


@views.route('/')
def home():
    return flask.render_template(
        'home.html',
        form=PropertiesForm(),
        identity=flask.session.get('identity'),
    )


@views.route('/data')
def data():
    the_data = cache.get('the_data')
    if the_data is None:
        the_data = github.get_data()
        cache.set('the_data', the_data)
    return flask.jsonify(the_data)


def update_feature(data):
    document = github.get_data()
    for feature in document['features']:
        properties = feature['properties']
        if properties['id'] == data['id']:
            break
    else:
        raise RuntimeError("Feature not found: %d", data['id'])
    properties.update(data)
    message = u"Edit via website\n\nIP address: %s" % flask.request.remote_addr
    github.commit(document, message)


@views.route('/save', methods=['POST'])
def save():
    form = PropertiesForm()
    if form.validate_on_submit():
        update_feature(form.data)
        cache.clear()
        return flask.jsonify(ok=True)
    else:
        return flask.jsonify(ok=False)


def setup_oauth(app):
    oauth = OAuth(app)
    google = oauth.remote_app(
        'google',
        consumer_key=app.config.get('GOOGLE_OAUTH_KEY'),
        consumer_secret=app.config.get('GOOGLE_OAUTH_SECRET'),
        request_token_params={
            'scope': 'https://www.googleapis.com/auth/userinfo.email'},
        base_url='https://www.googleapis.com/oauth2/v1/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
    )

    @app.route('/login')
    def login():
        url = flask.url_for('authorized', _external=True)
        return google.authorize(callback=url)

    @app.route('/logout')
    def logout():
        flask.session.pop('identity', None)
        return flask.redirect(flask.url_for('views.home'))

    @app.route('/login/google')
    @google.authorized_handler
    def authorized(resp):
        if resp is None:
            return 'Access denied: reason=%s error=%s' % (
                flask.request.args['error_reason'],
                flask.request.args['error_description'],
            )
        flask.session['identity'] = {
            'google_token': (resp['access_token'], ''),
        }
        me = google.get('userinfo')
        flask.session['identity']['name'] = me.data['name']
        flask.session['identity']['email'] = me.data['email']
        flask.session['identity']['picture'] = me.data['picture']
        return flask.redirect(flask.url_for('views.home'))

    @google.tokengetter
    def get_google_oauth_token():
        return flask.session.get('identity', {}).get('google_token')


def create_app():
    app = flask.Flask(__name__)
    app.config.from_pyfile('settings.py', silent=True)
    setup_oauth(app)
    app.register_blueprint(views)
    return app


def create_manager(app):
    manager = Manager(app)
    return manager
