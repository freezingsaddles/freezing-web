"""
Some authentication-related utility functions/classes.
"""
import logging
from functools import wraps

from flask import session, g
from werkzeug.exceptions import Forbidden


def login_athlete(strava_athlete):
    session['athlete_id'] = strava_athlete.id
    session['athlete_avatar'] = strava_athlete.profile_medium
    session['athlete_fname'] = strava_athlete.firstname
    g.logged_in = True


def requires_auth(f):
    """
    Decorator for view functions that require authentication.
    :param f:
    :return:
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not g.logged_in:
            logging.error("Unauthorized access.")
            raise Forbidden("This page requires authentication.")
        else:
            logging.info("User is logged in! {}".format(session.get('athlete_id')))
        return f(*args, **kwargs)
    return wrapper