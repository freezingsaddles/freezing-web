'''
Created on Feb 10, 2013

@author: hans
'''
import json
import copy
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from flask import render_template, redirect, url_for, current_app, request, Blueprint, session

from sqlalchemy import text
from dateutil import rrule, parser 

from stravalib import Client
from stravalib import unithelper as uh

from bafs import app, db, data
from bafs.utils import gviz_api
from bafs.model import Team, Athlete
from people import people_list_users, people_show_person, ridedays
from pointless import averagespeed, shortride, billygoat, tortoiseteam, weekendwarrior


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
    q = text ("""select count(*) as num_contestants from athletes WHERE team_id is not null""")
    
    indiv_count_res = db.session.execute(q).fetchone() # @UndefinedVariable
    contestant_count = indiv_count_res['num_contestants']

    q = text ("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time,
                  coalesce(sum(R.distance),0) as distance
                from rides R
                ;
            """)
    
    all_res = db.session.execute(q).fetchone() # @UndefinedVariable
    total_miles = int(all_res['distance'])
    total_hours = uh.timedelta_to_seconds(timedelta(seconds=int(all_res['moving_time']))) / 3600
    total_rides = all_res['num_rides']
     
    q = text ("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R 
                join ride_weather W on W.ride_id = R.id
                where W.ride_temp_avg < 32
                ;
            """)
    
    sub32_res = db.session.execute(q).fetchone() # @UndefinedVariable
    sub_freezing_hours = uh.timedelta_to_seconds(timedelta(seconds=int(sub32_res['moving_time']))) / 3600
    
    q = text ("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R 
                join ride_weather W on W.ride_id = R.id
                where W.ride_rain = 1
                ;
            """)
    
    rain_res = db.session.execute(q).fetchone() # @UndefinedVariable
    rain_hours = uh.timedelta_to_seconds(timedelta(seconds=int(rain_res['moving_time']))) / 3600
    
    q = text ("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R 
                join ride_weather W on W.ride_id = R.id
                where W.ride_snow = 1
                ;
            """)
    
    snow_res = db.session.execute(q).fetchone() # @UndefinedVariable
    snow_hours = uh.timedelta_to_seconds(timedelta(seconds=int(snow_res['moving_time']))) / 3600
    
    
    return render_template('index.html',
                           team_count=len(app.config['BAFS_TEAMS']),
                           contestant_count=contestant_count,
                           total_rides=total_rides,
                           total_hours=total_hours,
                           total_miles=total_miles,
                           rain_hours=rain_hours,
                           snow_hours=snow_hours,
                           sub_freezing_hours=sub_freezing_hours)

@blueprint.route("/login")
def login():
    c = Client()
    url = c.authorization_url(client_id=app.config['STRAVA_CLIENT_ID'],
                              redirect_uri=url_for('.logged_in', _external=True),
                              approval_prompt='auto')
    return render_template('login.html', authorize_url=url)

@blueprint.route("/logout")
def logout():
    session.clear()


@blueprint.route("/strava-oauth")
def logged_in():
    """
    Method called by Strava (redirect) that includes parameters.
    - state
    - code
    - error
    """
    error = request.args.get('error')
    state = request.args.get('state')
    if error:
        return render_template('login_error.html', error=error)
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

        # TODO: Actually process the login, set data in session
        if not no_teams:
            session['athlete_id'] = strava_athlete.id
            session['athlete_avatar'] = strava_athlete.profile_medium
            session['athlete_fname'] = strava_athlete.firstname

        return render_template('login_results.html', athlete=strava_athlete,
                               team=team, multiple_teams=multiple_teams,
                               no_teams=no_teams)

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

@blueprint.route("/pointless/avgspeed")
def average_speed():
    return averagespeed()    

@blueprint.route("/pointless/avgdist")
def average_distance():
    return shortride()  

@blueprint.route("/pointless/billygoat")
def billy_goat():
    return billygoat()   

@blueprint.route("/pointless/tortoiseteam")
def tortoise_team():
    return tortoiseteam() 

@blueprint.route("/pointless/weekend")
def wknd():
    return weekendwarrior() 
