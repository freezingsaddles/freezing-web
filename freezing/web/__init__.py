import os
import os.path

from flask import Flask, session, g
from freezing.model import init_model

from .config import config

app = Flask(__name__, static_url_path='/assets')
app.config.from_object(config)

init_model(config.SQLALCHEMY_URL)

# This needs to be after the app is created, unfortunately.
from freezing.web.views import general, leaderboard, chartdata, people, user, pointless, photos, api, alt_scoring
from freezing.web.utils import auth

# Register our blueprints

app.register_blueprint(general.blueprint)
app.register_blueprint(leaderboard.blueprint, url_prefix='/leaderboard')
app.register_blueprint(alt_scoring.blueprint, url_prefix='/alt_scoring')
app.register_blueprint(chartdata.blueprint, url_prefix='/chartdata')
app.register_blueprint(people.blueprint, url_prefix='/people')
app.register_blueprint(pointless.blueprint, url_prefix='/pointless')
app.register_blueprint(photos.blueprint, url_prefix='/photos')
app.register_blueprint(user.blueprint, url_prefix='/my')
app.register_blueprint(api.blueprint, url_prefix='/api')


@app.before_request
def set_logged_in_global():
    if session.get('athlete_id'):
        g.logged_in = True
    else:
        g.logged_in = False
