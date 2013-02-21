'''
Created on Feb 10, 2013

@author: hans
'''
import json
import copy
from collections import defaultdict
from datetime import datetime

from flask import render_template, redirect, url_for, current_app, request

from sqlalchemy import text
from dateutil import rrule, parser 

from bafs import app, db
from bafs.utils import gviz_api
from bafs.model import Team

@app.route("/")
def index():
    return redirect(url_for('team_leaderboard'))

@app.route("/leaderboard")
def leaderboard():
    return redirect(url_for('team_leaderboard'))

@app.route("/leaderboard/team")
def team_leaderboard():
    return render_template('leaderboard/team.html')

@app.route("/leaderboard/team_elev")
def team_elev_leaderboard():
    return render_template('leaderboard/team_elev.html')

@app.route("/leaderboard/individual")
def indiv_leaderboard():
    return render_template('leaderboard/indiv.html')

@app.route("/leaderboard/individual_elev")
def indiv_elev_leaderboard():
    return render_template('leaderboard/indiv_elev.html')

@app.route("/trends")
def trends():
    return redirect(url_for('team_cumul_trend'))

@app.route("/trends/team_cumul")
def team_cumul_trend():
    return render_template('trends/team_cumul.html')

@app.route("/chartdata/team_leaderboard")
def team_leaderboard_data():
    """
    Loads the leaderboard data broken down by team.
    """
    q = text("""
             select T.id as team_id, T.name as team_name, sum(DS.points) as total_score
             from daily_scores DS 
             join teams T on T.id = DS.team_id 
             group by T.id, T.name
             order by total_score desc
             ;
             """)
    
    team_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'team_name', 'label': 'Team', 'type': 'string'},
            {'id': 'score', 'label': 'Score', 'type': 'number'},
            # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
            ]
    
    rows = []
    for i,res in enumerate(team_q):
        place = i+1
        cells = [{'v': res['team_name'], 'f': '{0} [{1}]'.format(res['team_name'], place)},
                 {'v': res['total_score'], 'f': str(int(res['total_score']))}]
        rows.append({'c': cells})
        
    
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@app.route("/chartdata/indiv_leaderboard")
def indiv_leaderboard_data():
    """
    Loads the leaderboard data broken down by team.
    """
    q = text("""
             select A.id as athlete_id, A.name as athlete_name, sum(DS.points) as total_score
             from daily_scores DS 
             join athletes A on A.id = DS.athlete_id
             group by A.id, A.name
             order by total_score desc
             ;
             """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Elevation', 'type': 'number'},
            # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) }, {'v': res['total_score'], 'f': str(int(res['total_score']))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@app.route("/chartdata/team_elev_gain")
def team_elev_gain():
    q = text ("""
        select T.id, T.name as team_name, sum(R.elevation_gain) as cumul_elev_gain
        from rides R
        join athletes A on A.id = R.athlete_id
        join teams T on T.id = A.team_id
        group by T.id, team_name
        order by cumul_elev_gain desc
        ;
        """)
    
    team_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Score', 'type': 'number'},
            # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
            ]
    
    rows = []
    for i,res in enumerate(team_q):
        place = i+1
        cells = [{'v': res['team_name'], 'f': '{0} [{1}]'.format(res['team_name'], place)},
                 {'v': res['cumul_elev_gain'], 'f': str(int(res['cumul_elev_gain']))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@app.route("/chartdata/indiv_elev_gain")
def indiv_elev_gain():
    
    q = text ("""
                select R.athlete_id, A.name as athlete_name, sum(R.elevation_gain) as cumul_elev_gain
                from rides R
                join athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by cumul_elev_gain desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Elevation', 'type': 'number'},
            # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) }, {'v': res['cumul_elev_gain'], 'f': str(int(res['cumul_elev_gain']))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})
        
@app.route("/chartdata/team_cumul_points")
def team_cumul_points():
    """
    """
    teams = db.session.query(Team).all() # @UndefinedVariable
    
    q = text("""
            select team_id, ride_date, points,
                     (@total_points := @total_points + points) AS cumulative_points,
                     (@total_distance := @total_distance + points) AS cumulative_distance
             from daily_scores, (select @total_points := 0, @total_distance := 0) AS vars
             where team_id = :team_id
             order by ride_date;             
             """)
            
    cols = [{'id': 'date', 'label': 'Date', 'type': 'date'}]
    
    for team in teams:
        cols.append({'id': 'team_{0}'.format(team.id), 'label': team.name, 'type': 'number'})

    tpl_dict = dict([(dt.strftime('%Y-%m-%d'), None) for dt in rrule.rrule(rrule.DAILY, dtstart=parser.parse(app.config['BAFS_START_DATE']), until=datetime.now())])  
        
    # Query for each team, build this into a multidim array
    daily_cumul = defaultdict(dict)
    
    for team in teams:
        daily_cumul[team.id] = copy.copy(tpl_dict) # Ensure that we have keys for every day (even if there were no rides for that day)
        for row in db.engine.execute(q, team_id=team.id).fetchall(): # @UndefinedVariable
            daily_cumul[team.id][row['ride_date'].strftime('%Y-%m-%d')] = row['cumulative_points']
            
        # Fill in any None gaps with the previous non-None value
        prev_value = 0
        for datekey in sorted(tpl_dict.keys()):
            if daily_cumul[team.id][datekey] is None:
                daily_cumul[team.id][datekey] = prev_value
            else:
                prev_value = daily_cumul[team.id][datekey]
        
    rows = []
    for datekey in sorted(tpl_dict.keys()):
        cells = [{'v': parser.parse(datekey).date() }]
        for team in teams:
            cells.append({'v': daily_cumul[team.id][datekey]})
        rows.append({'c': cells})

    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@app.route("/chartdata/team_cumul_mileage")
def team_cumul_mileage():
    """
    """
    teams = db.session.query(Team).all() # @UndefinedVariable
    
    q = text("""
            select team_id, ride_date, points,
                     (@total_points := @total_points + points) AS cumulative_points,
                     (@total_distance := @total_distance + points) AS cumulative_distance
             from daily_scores, (select @total_points := 0, @total_distance := 0) AS vars
             where team_id = :team_id
             order by ride_date;             
             """)
            
    cols = [{'id': 'date', 'label': 'Date', 'type': 'date'}]
    
    for team in teams:
        cols.append({'id': 'team_{0}'.format(team.id), 'label': team.name, 'type': 'number'})

    tpl_dict = dict([(dt.strftime('%Y-%m-%d'), None) for dt in rrule.rrule(rrule.DAILY, dtstart=parser.parse(app.config['BAFS_START_DATE']), until=datetime.now())])  
        
    # Query for each team, build this into a multidim array
    daily_cumul = defaultdict(dict)
    
    for team in teams:
        daily_cumul[team.id] = copy.copy(tpl_dict) # Ensure that we have keys for every day (even if there were no rides for that day)
        for row in db.engine.execute(q, team_id=team.id).fetchall(): # @UndefinedVariable
            daily_cumul[team.id][row['ride_date'].strftime('%Y-%m-%d')] = row['cumulative_distance']
            
        # Fill in any None gaps with the previous non-None value
        prev_value = 0
        for datekey in sorted(tpl_dict.keys()):
            if daily_cumul[team.id][datekey] is None:
                daily_cumul[team.id][datekey] = prev_value
            else:
                prev_value = daily_cumul[team.id][datekey]
        
    rows = []
    for datekey in sorted(tpl_dict.keys()):
        cells = [{'v': parser.parse(datekey).date() }]
        for team in teams:
            cells.append({'v': daily_cumul[team.id][datekey]})
        rows.append({'c': cells})

    return gviz_api_jsonify({'cols': cols, 'rows': rows})

def gviz_api_jsonify(*args, **kwargs):
    """Creates a :class:`~flask.Response` with the JSON representation of
    the given arguments with an `application/json` mimetype.  The arguments
    to this function are the same as to the :class:`dict` constructor.

    Example usage::

        @app.route('/_get_current_user')
        def get_current_user():
            return jsonify(username=g.user.username,
                           email=g.user.email,
                           id=g.user.id)

    This will send a JSON response like this to the browser::

        {
            "username": "admin",
            "email": "admin@localhost",
            "id": 42
        }

    This requires Python 2.6 or an installed version of simplejson.  For
    security reasons only objects are supported toplevel.  For more
    information about this, have a look at :ref:`json-security`.

    .. versionadded:: 0.2
    """
    return current_app.response_class(json.dumps(dict(*args, **kwargs),
                                                 indent=None if request.is_xhr else 2, cls=gviz_api.DataTableJSONEncoder),
                                      mimetype='application/json')