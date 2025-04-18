"""
Some authentication-related utility functions/classes.
"""

import logging
from datetime import timedelta
from functools import update_wrapper, wraps

from flask import current_app, g, make_response, request, session
from werkzeug.exceptions import Forbidden


def login_athlete(strava_athlete):
    # mobile devices delete transient cookies frequently so prefer a persistent cookie
    session.permanent = True  # 128-day (see config) cookie instead of transient
    session["athlete_id"] = strava_athlete.id
    session["athlete_avatar"] = strava_athlete.profile_medium
    session["athlete_fname"] = strava_athlete.firstname
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
            logging.info("User is logged in! {}".format(session.get("athlete_id")))
        return f(*args, **kwargs)

    return wrapper


def crossdomain(
    origin=None,
    methods=None,
    headers=None,
    max_age=21600,
    attach_to_all=True,
    automatic_options=True,
):
    if methods is not None:
        methods = ", ".join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, str):
        headers = ", ".join(x.upper() for x in headers)
    if not isinstance(origin, str):
        origin = ", ".join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers["allow"]

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == "OPTIONS":
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != "OPTIONS":
                return resp

            h = resp.headers

            h["Access-Control-Allow-Origin"] = origin
            h["Access-Control-Allow-Methods"] = get_methods()
            h["Access-Control-Max-Age"] = str(max_age)
            if headers is not None:
                h["Access-Control-Allow-Headers"] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)

    return decorator
