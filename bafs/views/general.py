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
from bafs.model import Team, Athlete
from people import people_list_users, people_show_person, ridedays


blueprint = Blueprint('general', __name__)

class AccessDenied(RuntimeError):
    pass

@app.template_filter('groupnum')
def groupnum(number):
    s = '%d' % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

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
        athlete_model = data.register_athlete(strava_athlete, access_token)
        multiple_teams = None
        no_teams = False
        team = None
        try:
            team = data.register_athlete_team(strava_athlete=strava_athlete, athlete_model=athlete_model)
        except data.MultipleTeamsError as multx:
            multiple_teams = multx.teams
        except data.NoTeamsError:
            no_teams = True
            
        
        return render_template('authorization_success.html', athlete=strava_athlete,
                               team=team, multiple_teams=multiple_teams,
                               no_teams=no_teams)

@blueprint.route("/leaderboard")
def leaderboard():
    return redirect(url_for('.team_leaderboard'))

@blueprint.route("/leaderboard/team")
def team_leaderboard():
    return render_template('leaderboard/team.html')

@blueprint.route("/leaderboard/team_text")
def team_leaderboard_classic():
    # Get teams sorted by points
    q = text("""
             select T.id as team_id, T.name as team_name, sum(DS.points) as total_score,
             sum(DS.distance) as total_distance
             from daily_scores DS 
             join teams T on T.id = DS.team_id 
             group by T.id, T.name
             order by total_score desc
             ;
             """)
    
    team_rows = db.session.execute(q).fetchall() # @UndefinedVariable
    
    q = text("""
             select A.id as athlete_id, A.team_id, A.display_name as athlete_name,
             sum(DS.points) as total_score, sum(DS.distance) as total_distance,
             count(DS.points) as days_ridden
             from daily_scores DS 
             join athletes A on A.id = DS.athlete_id
             group by A.id, A.display_name
             order by total_score desc
             ;
             """)
    
    team_members = {}
    for indiv_row in db.session.execute(q).fetchall(): # @UndefinedVariable 
        team_members.setdefault(indiv_row['team_id'], []).append(indiv_row)
    
    for team_id in team_members:
        team_members[team_id] = reversed(sorted(team_members[team_id], key=lambda m: m['total_score']))
    
    return render_template('leaderboard/team_text.html', team_rows=team_rows, team_members=team_members)

@blueprint.route("/leaderboard/team_various")
def team_leaderboard_various():
    return render_template('leaderboard/team_various.html')

@blueprint.route("/leaderboard/individual")
def indiv_leaderboard():
    return render_template('leaderboard/indiv.html')

@blueprint.route("/leaderboard/individual_text")
def individual_leaderboard_text():
    
    q = text("""
             select A.id as athlete_id, A.team_id, A.display_name as athlete_name,
             sum(DS.distance) as total_distance, sum(DS.points) as total_score,
             count(DS.points) as days_ridden
             from daily_scores DS 
             join athletes A on A.id = DS.athlete_id
             group by A.id, A.display_name
             order by total_score desc
             ;
             """)
        
    indiv_rows = db.session.execute(q).fetchall() # @UndefinedVariable 
        
    return render_template('leaderboard/indiv_text.html', indiv_rows=indiv_rows)

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

@blueprint.route("/people")
def list_users():
    return people_list_users()

@blueprint.route("/people/<user_id>")
def show_user(user_id):
    return people_show_person(user_id)
    
@blueprint.route("/people/ridedays")
def ride_days():
	return ridedays()
	
