'''
Created on Feb 10, 2013

@author: hans
'''
import json
import copy
from collections import defaultdict
from datetime import datetime

from flask import render_template, redirect, url_for, current_app, request, Blueprint

from sqlalchemy import text
from dateutil import rrule, parser 

from stravalib import Client

from bafs import app, db, data
from bafs.utils import gviz_api
from bafs.model import Team

blueprint = Blueprint('general', __name__)

class AccessDenied(RuntimeError):
    pass

@blueprint.route("/")
def index():
    return render_template('index.html')

@blueprint.route("/authorize")
def join():
    c = Client()
    url = c.authorization_url(client_id=app.config['STRAVA_CLIENT_ID'],
                              redirect_uri=url_for('.authorization', _external=True),
                              approval_prompt='auto')
    return render_template('authorize.html', authorize_url=url)

@blueprint.route("/authorization")
def authorization():
    """
    Method called by Strava (redirect) that includes parameters.
    - state
    - code
    - error
    """
    error = request.args.get('error')
    state = request.args.get('state')
    if error:
        return render_template('authorization_error.html', error=error)
    else:
        code = request.args.get('code')
        client = Client()
        access_token = client.exchange_code_for_token(client_id=app.config['STRAVA_CLIENT_ID'],
                                                      client_secret=app.config['STRAVA_CLIENT_SECRET'],
                                                      code=code)
        # Use the now-authenticated client to get the current athlete
        strava_athlete = client.get_athlete()
        data.register_athlete(strava_athlete, access_token)
        return render_template('authorization_success.html', athlete=strava_athlete)

@blueprint.route("/leaderboard")
def leaderboard():
    return redirect(url_for('.team_leaderboard'))

@blueprint.route("/leaderboard/team")
def team_leaderboard():
    return render_template('leaderboard/team.html')

@blueprint.route("/leaderboard/team_various")
def team_leaderboard_various():
    return render_template('leaderboard/team_various.html')

@blueprint.route("/leaderboard/individual")
def indiv_leaderboard():
    return render_template('leaderboard/indiv.html')


@blueprint.route("/leaderboard/individual_various")
def indiv_leaderboard_various():
    return render_template('leaderboard/indiv_various.html')

@blueprint.route("/explore")
def trends():
    return redirect(url_for('.team_cumul_trend'))

@blueprint.route("/explore/team_cumul")
def team_cumul_trend():
    return render_template('explore/team_cumul.html')

@blueprint.route("/explore/team_weekly")
def team_weekly_points():
    return render_template('explore/team_weekly_points.html')

@blueprint.route("/explore/indiv_elev_dist")
def indiv_elev_dist():
    return render_template('explore/indiv_elev_dist.html')

@blueprint.route("/explore/riders_by_lowtemp")
def riders_by_lowtemp():
    return render_template('explore/riders_by_lowtemp.html')
