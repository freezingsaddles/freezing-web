from flask import Flask, g, session
from freezing.model import init_model, meta

from .config import config

# Thanks https://stackoverflow.com/a/17073583
app = Flask(__name__, static_folder="static", static_url_path="/")
app.config.from_object(config)

init_model(config.SQLALCHEMY_URL)

# This needs to be after the app is created, unfortunately.
from freezing.web.views import (  # noqa
    alt_scoring,
    api,
    chartdata,
    general,
    leaderboard,
    people,
    photos,
    pointless,
    tribes,
    user,
)

# Register our blueprints

app.register_blueprint(general.blueprint)
app.register_blueprint(leaderboard.blueprint, url_prefix="/leaderboard")
app.register_blueprint(alt_scoring.blueprint, url_prefix="/alt_scoring")
app.register_blueprint(chartdata.blueprint, url_prefix="/chartdata")
app.register_blueprint(people.blueprint, url_prefix="/people")
app.register_blueprint(pointless.blueprint, url_prefix="/pointless")
app.register_blueprint(photos.blueprint, url_prefix="/photos")
app.register_blueprint(user.blueprint, url_prefix="/my")
app.register_blueprint(api.blueprint, url_prefix="/api")
app.register_blueprint(tribes.blueprint, url_prefix="/tribes")


@app.before_request
def set_logged_in_global():
    if session.get("athlete_id"):
        g.logged_in = True
    else:
        g.logged_in = False


@app.teardown_request
def teardown_request(exception):
    session = meta.scoped_session()
    if exception:
        session.rollback()
    else:
        session.commit()
    meta.scoped_session.remove()


@app.context_processor
def inject_config():
    return {
        "competition_title": config.COMPETITION_TITLE,
        "registration_site": config.REGISTRATION_SITE,
        "forum_site": config.FORUM_SITE,
        "version_string": config.VERSION_STRING,
    }
