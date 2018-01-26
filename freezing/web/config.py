from typing import List
from datetime import datetime, tzinfo
from envparse import env

import arrow
import pytz


class Config:

    DEBUG: bool = env('DEBUG', cast=bool, default=False)
    SECRET_KEY = env('SECRET_KEY')

    SQLALCHEMY_URL = env('SQLALCHEMY_URL')
    BEANSTALKD_HOST = env('BEANSTALKD_HOST', default='beanstalkd.container')
    BEANSTALKD_PORT: int = env('BEANSTALKD_PORT', cast=int, default=11300)

    STRAVA_CLIENT_ID = env('STRAVA_CLIENT_ID')
    STRAVA_CLIENT_SECRET = env('STRAVA_CLIENT_SECRET')

    COMPETITION_TEAMS: List[int] = env('TEAMS', cast=list, subcast=int, default=[])
    OBSERVER_TEAMS: List[int] = env('OBSERVER_TEAMS', cast=list, subcast=int, default=[])

    START_DATE: datetime = env('START_DATE', postprocessor=lambda val: arrow.get(val).datetime)
    END_DATE: datetime = env('END_DATE', postprocessor=lambda val: arrow.get(val).datetime)
    TIMEZONE: tzinfo = env('TIMEZONE', default='America/New_York', postprocessor=lambda val: pytz.timezone(val))
