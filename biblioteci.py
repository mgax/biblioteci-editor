# encoding: utf-8
import logging
import flask
from flask.ext.script import Manager
from flask.ext.wtf import Form
from flask.ext.oauthlib.client import OAuth
from raven.contrib.flask import Sentry
from werkzeug.contrib.cache import SimpleCache
from wtforms import TextField, IntegerField
from wtforms.widgets import HiddenInput, TextArea
import requests
import github

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cache = SimpleCache()


class PropertiesForm(Form):
    id = IntegerField(widget=HiddenInput())
    name = TextField(u"Nume")
    description = TextField(u"Descriere", widget=TextArea())
    address = TextField(u"Adresă")
    locality = TextField(u"Localitate")
    website_url = TextField(u"Website")
    catalog_url = TextField(u"Catalog")
    facebook_url = TextField(u"Facebook")
    open_hours = TextField(u"Program")


views = flask.Blueprint('views', __name__)


def get_identity():
    config = flask.current_app.config
    return flask.session.get('identity', config.get('IDENTITY_DEBUG'))


@views.route('/')
def home():
    return flask.render_template(
        'home.html',
        form=PropertiesForm(),
        identity=get_identity(),
    )


@views.route('/_crashme', methods=['GET', 'POST'])
def crashme():
    if flask.request.method == 'POST':
        raise RuntimeError("crashing as requested")
    return '<form method="POST"><button type="submit">crashme</button></form>'


@views.route('/data')
def data():
    the_data = cache.get('the_data')
    if the_data is None:
        the_data = github.get_data()
        cache.set('the_data', the_data)
    return flask.jsonify(the_data)


def update_geojson(new_properties, lat, lng):
    document = github.get_data()

    if new_properties['id'] == -1:
        last_id = max(f['properties'].get('id', 0)
                      for f in document['features'])
        new_properties['id'] = last_id + 1
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': "Point",
                'coordinates': [float(lng), float(lat)],
            },
            'properties': new_properties,
        }
        document['features'].append(feature)

    else:
        for feature in document['features']:
            properties = feature['properties']
            if properties['id'] == new_properties['id']:
                break
        else:
            raise RuntimeError("Feature not found: %d", new_properties['id'])

        properties.update(new_properties)

    identity = get_identity()
    author = {'name': identity['name'], 'email': identity['email']}
    github.commit(document, u"Edit via website", author)

    return feature


@views.route('/save', methods=['POST'])
def save():
    form = PropertiesForm()
    if form.validate_on_submit():
        lat = flask.request.form.get('lat', type=float)
        lng = flask.request.form.get('lng', type=float)
        feature = update_geojson(form.data, lat, lng)
        cache.clear()
        return flask.jsonify(ok=True, feature=feature)
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
    Sentry(app)
    app.register_blueprint(views)
    return app


def create_manager(app):
    manager = Manager(app)
    return manager
