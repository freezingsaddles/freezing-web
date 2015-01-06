"""
Some authentication-related utility functions/classes.
"""

from flask import session, g

def login_athlete(strava_athlete):
    session['athlete_id'] = strava_athlete.id
    session['athlete_avatar'] = strava_athlete.profile_medium
    session['athlete_fname'] = strava_athlete.firstname
    g.logged_in = True