"""
Some authentication-related utility functions/classes.
"""

from flask import session

def logged_in_user():
    if session['strava_athlete']:
        return session['strava_athlete']
    else:
        return None

class AuthenticatedUser(object):

    def __init__(self, id=None, name=None, team_id=None, team_name=None, profile_photo=None):
        self.id = id
        self.name = name
        self.team_id = team_id
        self.team_name = team_name
        self.profile_photo = profile_photo

    def __repr__(self):
        return '<%s id={} name={}>'.format(self.id, self.name)

