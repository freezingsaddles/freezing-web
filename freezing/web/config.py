import logging
import os
from datetime import datetime, tzinfo
from typing import List

import arrow
import pytz
from colorlog import ColoredFormatter
from envparse import env

envfile = os.environ.get("APP_SETTINGS", os.path.join(os.getcwd(), ".env"))

if os.path.exists(envfile):
    env.read_envfile(envfile)

_basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class Config:
    DEBUG: bool = env("DEBUG", cast=bool, default=False)
    SECRET_KEY = env("SECRET_KEY")

    SQLALCHEMY_URL = env("SQLALCHEMY_URL")
    BEANSTALKD_HOST = env("BEANSTALKD_HOST", default="localhost")
    BEANSTALKD_PORT = env("BEANSTALKD_PORT", cast=int, default=11300)

    STRAVA_CLIENT_ID = env("STRAVA_CLIENT_ID")
    STRAVA_CLIENT_SECRET = env("STRAVA_CLIENT_SECRET")

    COMPETITION_TITLE = env("COMPETITION_TITLE", default="Freezing Saddles")
    COMPETITION_TEAMS: List[int] = env("TEAMS", cast=list, subcast=int, default=[])
    OBSERVER_TEAMS: List[int] = env(
        "OBSERVER_TEAMS", cast=list, subcast=int, default=[]
    )
    MAIN_TEAM: int = env("MAIN_TEAM", cast=int)

    START_DATE: datetime = env(
        "START_DATE", postprocessor=lambda val: arrow.get(val).datetime
    )
    END_DATE: datetime = env(
        "END_DATE", postprocessor=lambda val: arrow.get(val).datetime
    )
    TIMEZONE: tzinfo = env(
        "TIMEZONE",
        default="America/New_York",
        postprocessor=lambda val: pytz.timezone(val),
    )

    LEADERBOARDS_DIR = env(
        "LEADERBOARDS_DIR", default=os.path.join(_basedir, "leaderboards")
    )

    REGISTRATION_SITE: str = env("REGISTRATION_SITE", "https://freezingsaddles.info/")


config = Config()


def init_logging(loglevel: int = logging.INFO, color: bool = False):
    """
    Initialize the logging subsystem and create a logger for this class, using passed in optparse options.

    :param level: The log level (e.g. logging.DEBUG)
    :return:
    """

    ch = logging.StreamHandler()
    ch.setLevel(loglevel)

    if color:
        formatter = ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s [%(name)s] %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            },
        )
    else:
        formatter = logging.Formatter("%(levelname)-8s [%(name)s] %(message)s")

    ch.setFormatter(formatter)

    loggers = [
        logging.getLogger("freezing"),
        logging.getLogger("stravalib"),
        logging.getLogger("requests"),
        logging.root,
    ]

    for logger in loggers:
        if logger is logging.root:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        logger.addHandler(ch)
