import logging
import os
from datetime import datetime, tzinfo
from importlib.metadata import version
from typing import List

import arrow
import pytz
from colorlog import ColoredFormatter
from envparse import env

from .version import branch, build_date, commit

envfile = os.environ.get("APP_SETTINGS", os.path.join(os.getcwd(), ".env"))

if os.path.exists(envfile):
    env.read_envfile(envfile)

_basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class Config:
    """
    Configuration for the application. These can be overridden by setting the appropriate environment variables.

    Refactored with the help of GitHub Copilot.
    """

    BEANSTALKD_HOST = env("BEANSTALKD_HOST", default="localhost")
    BEANSTALKD_PORT = env("BEANSTALKD_PORT", cast=int, default=11300)
    COMPETITION_TEAMS: List[int] = env("TEAMS", cast=list, subcast=int, default=[])
    COMPETITION_TITLE = env("COMPETITION_TITLE", default="Freezing Saddles")
    DEBUG: bool = env("DEBUG", cast=bool, default=False)
    END_DATE: datetime = env(
        "END_DATE", postprocessor=lambda val: arrow.get(val).datetime
    )
    # Environment (localdev, production, etc.)
    ENVIRONMENT = env("ENVIRONMENT", default="localdev")
    FORUM_SITE: str = env(
        "FORUM_SITE",
        "https://www.bikearlingtonforum.com/forums/forum/freezing-saddles-winter-riding-competition/",
    )
    INSTANCE_PATH = env(
        "INSTANCE_PATH", default=os.path.join(_basedir, "data/instance")
    )
    # Directory to store leaderboard data
    LEADERBOARDS_DIR = env(
        "LEADERBOARDS_DIR", default=os.path.join(_basedir, "leaderboards")
    )
    MAIN_TEAM: int = env("MAIN_TEAM", cast=int)
    OBSERVER_TEAMS: List[int] = env(
        "OBSERVER_TEAMS", cast=list, subcast=int, default=[]
    )
    REGISTRATION_SITE: str = env("REGISTRATION_SITE", "https://freezingsaddles.info/")
    SECRET_KEY = env("SECRET_KEY")
    SQLALCHEMY_URL = env("SQLALCHEMY_URL")
    START_DATE: datetime = env(
        "START_DATE", postprocessor=lambda val: arrow.get(val).datetime
    )
    STRAVA_CLIENT_ID = env("STRAVA_CLIENT_ID")
    STRAVA_CLIENT_SECRET = env("STRAVA_CLIENT_SECRET")
    TIMEZONE: tzinfo = env(
        "TIMEZONE",
        default="America/New_York",
        postprocessor=lambda val: pytz.timezone(val),
    )
    VERSION_NUM = version("freezing-web")
    VERSION_STRING = f"{VERSION_NUM}+{branch}.{commit}.{build_date}"


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

    logger = logging.getLogger("freezing")
    loggers = [
        logger,
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

    logger.info(f"logging initialized for app version {config.VERSION_STRING}")
