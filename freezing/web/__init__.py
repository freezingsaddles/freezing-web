"""
This is the main entry point for the freezing-web application.

It sets up the Flask app and initializes the database and logging.
It also sets up a fault handler with a signal early to ensure stack traces happen.
"""

import freezing.web._faulthandler  # noqa isort: skip

from socket import gethostbyname
from time import sleep
from urllib.parse import urlparse

from flask import Flask, g, session
from freezing.model import init_model, meta

from freezing.web.autolog import log

from .config import config, init_logging

init_logging(color=config.DEBUG is False)


_BANNER = "*************************"


def _get_app():
    log.info(
        f"{_BANNER} Configuring Flask app with instance_path={config.INSTANCE_PATH} {_BANNER}"
    )
    # Thanks https://stackoverflow.com/a/17073583
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/",
        instance_path=config.INSTANCE_PATH,
    )
    app.config.from_object(config)
    return app


def _register_blueprints(app):
    # This needs to be after the app is created, unfortunately.
    from freezing.web.views import (
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


# This has to be done before we define the functions with @app decorators
app = _get_app()
_register_blueprints(app)


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
        "environment": config.ENVIRONMENT,
        "registration_site": config.REGISTRATION_SITE,
        "forum_site": config.FORUM_SITE,
        "version_string": config.VERSION_STRING,
        "end_date": config.END_DATE,
    }


def init_db():
    """
    Initialize the database. If the database is not available, keep trying for a bit.
    """
    TRIES = 6
    delay = 2
    for x in range(1, TRIES + 1):
        try:
            # Use urllib to extract the host and test whether it can be resolved
            url = urlparse(config.SQLALCHEMY_URL)
            host = gethostbyname(url.hostname)
            log.debug(f"gethostbyname({url.hostname})=={host}")
            log.info(f"{_BANNER} Connecting to database on {url.hostname} {_BANNER}")
            init_model(config.SQLALCHEMY_URL)
            break
        except Exception as ex:
            if x == TRIES:
                raise ex from None
            log.warning(
                f"Failed to connect to database, retrying in {delay}s ({x}) - error was {str(ex)}"
            )
            delay = delay * 2
            sleep(delay)


init_db()

log.info(f"{_BANNER} freezing-web initialized in {config.ENVIRONMENT} mode {_BANNER}")
