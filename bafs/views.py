'''
Created on Feb 10, 2013

@author: hans
'''
from flask import render_template, jsonify, redirect, url_for

from sqlalchemy import text

from bafs import app, db
from bafs.utils import gviz_api

@app.route("/")
def index():
    return redirect(url_for('leaderboard'))

@app.route("/leaderboard")
def leaderboard():
    return render_template('leaderboard.html')

@app.route("/chartdata/team_leaderboard")
def team_leaderboard():
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
def indiv_leaderboard():
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