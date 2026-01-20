"""
This is the main entry point for the freezing-web application.

It sets up the Flask app and initializes the database and logging.
It also sets up a fault handler with a signal early to ensure stack traces happen.
"""

import freezing.web._faulthandler  # noqa isort: skip
import freezing.web.utils.sqlog  # noqa isort: skip

import os
from datetime import datetime
from socket import gethostbyname
from time import sleep
from typing import List
from urllib.parse import urlparse

import yaml
from flask import Flask, g, session
from freezing.model import init_model, meta
from freezing.model.msg import BaseMessage, BaseSchema
from freezing.model.orm import Athlete, Team
from marshmallow import fields

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
        api,
        chartdata,
        explore,
        general,
        leaderboard,
        people,
        photos,
        pointless,
        teams,
        tribes,
        user,
    )

    app.register_blueprint(general.blueprint)
    app.register_blueprint(leaderboard.blueprint, url_prefix="/leaderboard")
    app.register_blueprint(explore.blueprint, url_prefix="/explore")
    app.register_blueprint(chartdata.blueprint, url_prefix="/chartdata")
    app.register_blueprint(people.blueprint, url_prefix="/people")
    app.register_blueprint(pointless.blueprint, url_prefix="/pointless")
    app.register_blueprint(photos.blueprint, url_prefix="/photos")
    app.register_blueprint(user.blueprint, url_prefix="/my")
    app.register_blueprint(api.blueprint, url_prefix="/api")
    app.register_blueprint(teams.blueprint, url_prefix="/teams")
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


@app.before_request
def set_no_team_global():
    start = config.START_DATE.date()
    now_tz = datetime.now(config.TIMEZONE)
    today = min(now_tz, config.END_DATE).date()
    total_days = 1 + (today - start).days
    athlete_id = session.get("athlete_id")

    if athlete_id:
        team = (
            meta.scoped_session()
            .query(Team)
            .join(Athlete)
            .filter_by(id=athlete_id)
            .one()
        )
        g.no_team = (
            total_days <= 31 and team.leaderboard_exclude and config.COMPETITION_TEAMS
        )
    else:
        g.no_team = total_days <= 31 and config.COMPETITION_TEAMS


@app.teardown_request
def teardown_request(exception):
    session = meta.scoped_session()
    if exception:
        session.rollback()
    else:
        session.commit()
    meta.scoped_session.remove()


class PointlessCategory(BaseMessage):
    id: str | None = None
    name: str | None = None


class PointlessCategorySchema(BaseSchema):
    _model_class = PointlessCategory

    id = fields.Str(required=True)
    name = fields.Str(required=True)


class PointlessPrize(BaseMessage):
    url: str | None = None
    name: str | None = None
    discord: int | None = None
    category: str | None = None


class PointlessPrizeSchema(BaseSchema):
    _model_class = PointlessPrize

    url = fields.Str(required=True)
    name = fields.Str(required=True)
    discord = fields.Int()
    category = fields.Str(required=True)


class PointlessPrizes(BaseMessage):
    categories: List[PointlessCategory] = []
    prizes: List[PointlessPrize] = []

    def get(self, category: str) -> List[PointlessPrize]:
        prizes = [p for p in self.prizes if p.category == category]
        prizes.sort(key=lambda p: (p.name or "").lower())
        return prizes


class PointlessPrizesSchema(BaseSchema):
    _model_class = PointlessPrizes

    categories = fields.Nested(PointlessCategorySchema, many=True, required=True)
    prizes = fields.Nested(PointlessPrizeSchema, many=True, required=True)


def _load_pointless():
    # doesn't belong in leaderboards but guess what? idk
    path = os.path.join(config.LEADERBOARDS_DIR, "pointless.yml")
    with open(path, "rt", encoding="utf-8") as fp:
        doc = yaml.safe_load(fp)
    schema = PointlessPrizesSchema()
    prizes: PointlessPrizes = schema.load(doc)
    return prizes


@app.context_processor
def inject_config():
    return {
        "competition_title": config.COMPETITION_TITLE,
        "environment": config.ENVIRONMENT,
        "registration_site": config.REGISTRATION_SITE,
        "discord_invitation": config.DISCORD_INVITATION,
        "forum_site": config.FORUM_SITE,
        "version_string": config.VERSION_STRING,
        "end_date": config.END_DATE,
        "pointless_prizes": _load_pointless(),
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
