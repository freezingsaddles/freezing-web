import pytz

from datetime import datetime
from dateutil import parser as date_parser

from freezing.web import app, config


def parse_competition_timestamp(ts):
    """
    Parse the specified date/time (timestamp).

    If there is no explicit timezone in the timestamp, default to the competition timestamp.

    :param ts: The timestamp string.
    :type ts: str
    :return: The datetime object with time stampi
    :rtype: datetime
    """
    dt = date_parser.parse(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=config.TIMEZONE)
    return dt