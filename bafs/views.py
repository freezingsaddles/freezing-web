'''
Created on Feb 10, 2013

@author: hans
'''
import copy
from collections import defaultdict

from flask import render_template, jsonify, redirect, url_for

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

@app.route("/leaderboard/individual")
def indiv_leaderboard():
    return render_template('leaderboard/indiv.html')

@app.route("/leaderboard/trends")
def team_trends():
    return render_template('leaderboard/team_trends.html')

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
    
    team_q = db.session.execute(q).fetchall()
    
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
        
    
    return jsonify({'cols': cols, 'rows': rows})

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
    
    indiv_q = db.session.execute(q).fetchall()
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Score', 'type': 'number'},
            # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) }, {'v': res['total_score'], 'f': str(int(res['total_score']))}]
        rows.append({'c': cells})
        
    return jsonify({'cols': cols, 'rows': rows})

@app.route("/chartdata/team_mileage_trends")
def team_mileage_trend():
    """
    """
    teams = db.session.query(Team).all()
    
    q = text("""
             select date(R.start_date) as start_date, sum(R.distance) as mileage
             from rides R
             join athletes A on A.id = R.athlete_id
             where A.team_id = :team_id
             group by A.team_id, date(R.start_date)
             order by date(R.start_date)
             ;
             """)
    
    cols = [{'id': 'name', 'label': 'Date', 'type': 'date'}]
    
    for team in teams:
        cols.append({'id': 'team_{0}'.format(team.id), 'label': team.name, 'type': 'string'})

    tpl_dict = dict([(dt.strftime('%Y-%m-%d'), 0) for dt in rrule.rrule(rrule.DAILY, dtstart=parser.parse(app.config['BAFS_START_DATE']), until=parser.parse(app.config['BAFS_END_DATE']))])  
        
    # Query for each team, build this into a multidim array
    daily_totals = defaultdict(dict)
    
    for team in teams:
        daily_totals[team.id] = copy.copy(tpl_dict) # Ensure that we have keys for every day (even if there were no rides for that day)
        for row in db.engine.execute(q, team_id=team.id).fetchall():
            daily_totals[team.id][row['start_date'].strftime('%Y-%m-%d')] = row['mileage']
    
    helper_encoder = gviz_api.DataTableJSONEncoder()
    
    rows = []
    for datekey in tpl_dict.keys():
        for team in teams:
            # We want the order to be the same, so we don't just enumerate over the dict
            for row in daily_totals[team.id]:
                pass
            
        cells = [{'v': helper_encoder.default(parser.parse(datekey).date()) }]
        for team in teams:
            cells.append({'v': daily_totals[team.id][datekey]})
        rows.append({'c': cells})
            
    return jsonify({'cols': cols, 'rows': rows})

    