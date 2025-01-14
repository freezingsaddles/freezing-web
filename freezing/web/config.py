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

    BEANSTALKD_HOST: str = env("BEANSTALKD_HOST", default="localhost")
    BEANSTALKD_PORT: str = env("BEANSTALKD_PORT", cast=int, default=11300)
    BIND_INTERFACE: str = env("BIND_INTERFACE", default="127.0.0.1")
    COMPETITION_TEAMS: List[int] = env("TEAMS", cast=list, subcast=int, default=[])
    COMPETITION_TITLE: str = env("COMPETITION_TITLE", default="Freezing Saddles")
    DEBUG: bool = env("DEBUG", cast=bool, default=False)
    END_DATE: datetime = env(
        "END_DATE", postprocessor=lambda val: arrow.get(val).datetime
    )
    # Environment (localdev, production, etc.)
    ENVIRONMENT: str = env("ENVIRONMENT", default="localdev")
    FORUM_SITE: str = env(
        "FORUM_SITE",
        "https://www.bikearlingtonforum.com/forums/forum/freezing-saddles-winter-riding-competition/",
    )
    INSTANCE_PATH: str = env(
        "INSTANCE_PATH", default=os.path.join(_basedir, "data/instance")
    )
    # Directory to store leaderboard data
    LEADERBOARDS_DIR: str = env(
        "LEADERBOARDS_DIR", default=os.path.join(_basedir, "leaderboards")
    )
    MAIN_TEAM: int = env("MAIN_TEAM", cast=int)
    OBSERVER_TEAMS: List[int] = env(
        "OBSERVER_TEAMS", cast=list, subcast=int, default=[]
    )
    REGISTRATION_SITE: str = env("REGISTRATION_SITE", "https://freezingsaddles.info/")
    SECRET_KEY = env("SECRET_KEY")
    SQLALCHEMY_URL: str = env("SQLALCHEMY_URL")
    SQLALCHEMY_ROOT_URL: str = env("SQLALCHEMY_ROOT_URL", None)
    START_DATE: datetime = env(
        "START_DATE", postprocessor=lambda val: arrow.get(val).datetime
    )
    STRAVA_CLIENT_ID = env("STRAVA_CLIENT_ID")
    STRAVA_CLIENT_SECRET = env("STRAVA_CLIENT_SECRET")
    JSON_CACHE_DIR = env("JSON_CACHE_DIR", default=None)
    TIMEZONE: tzinfo = env(
        "TIMEZONE",
        default="America/New_York",
        postprocessor=lambda val: pytz.timezone(val),
    )
    VERSION_NUM: str = version("freezing-web")
    VERSION_STRING: str = f"{VERSION_NUM}+{branch}.{commit}.{build_date}"


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

    log_level_map = {
        "freezing": logging.DEBUG,
        "requests": logging.INFO,
        "stravalib": logging.INFO,
    }
    log_level_map["root"] = logging.DEBUG
    loggers = {k: logging.getLogger(k) for k in log_level_map.keys()}
    loggers.update({"root": logging.root})

    for k, logger in loggers.items():
        logger.setLevel(log_level_map[k])
    # logger.addHandler(ch)
    # logging.root.setLevel(loglevel)

    logging.root.addHandler(ch)

    print(f"loggers: {loggers}")

    logger.info(f"logging initialized for app version {config.VERSION_STRING}")
