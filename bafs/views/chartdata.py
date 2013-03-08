'''
Created on Feb 10, 2013

@author: hans
'''
import json
import copy
from collections import defaultdict
from datetime import datetime, timedelta

from flask import render_template, redirect, url_for, current_app, request, Blueprint

from sqlalchemy import text
from dateutil import rrule, parser 

from bafs import app, db
from bafs.utils import gviz_api
from bafs.model import Team, RideEffort

blueprint = Blueprint('chartdata', __name__)

@blueprint.route("/team_leaderboard")
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

@blueprint.route("/indiv_leaderboard")
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
            {'id': 'score', 'label': 'Score', 'type': 'number'},
            # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) }, {'v': res['total_score'], 'f': str(int(res['total_score']))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/team_elev_gain")
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

@blueprint.route("/indiv_elev_gain")
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

@blueprint.route("/indiv_moving_time")
def indiv_moving_time():
    
    q = text ("""
                select R.athlete_id, A.name as athlete_name, sum(R.moving_time) as total_moving_time
                from rides R
                join athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by total_moving_time desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Moving Time', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) },
                 {'v': res['total_moving_time'], 'f': str(timedelta(seconds=int(res['total_moving_time'])))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/team_moving_time")
def team_moving_time():
    
    q = text ("""
                select T.id, T.name as team_name, sum(R.moving_time) as total_moving_time
                from rides R
                join athletes A on A.id = R.athlete_id
                join teams T on T.id = A.team_id
                group by T.id, T.name
                order by total_moving_time desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Team', 'type': 'string'},
            {'id': 'score', 'label': 'Moving Time', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['team_name'], 'f': '{0} [{1}]'.format(res['team_name'], place) },
                 {'v': res['total_moving_time'], 'f': str(timedelta(seconds=int(res['total_moving_time'])))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/indiv_number_sleaze_days")
def indiv_number_sleaze_days():
    
    q = text ("""
                select D.athlete_id, A.name as athlete_name, count(*) as num_sleaze_days
                from daily_scores D
                join athletes A on A.id = D.athlete_id
                where D.points > 10 and D.points < 12
                group by D.athlete_id, athlete_name
                order by num_sleaze_days desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Sleaze Days', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) },
                 {'v': res['num_sleaze_days'], 'f': str(int(res['num_sleaze_days']))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/team_number_sleaze_days")
def team_number_sleaze_days():
    
    q = text ("""
                select T.id, T.name as team_name, count(*) as num_sleaze_days
                from daily_scores D
                join athletes A on A.id = D.athlete_id
                join teams T on T.id = A.team_id
                where D.points > 10 and D.points < 12
                group by T.id, T.name
                order by num_sleaze_days desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Team', 'type': 'string'},
            {'id': 'score', 'label': 'Sleaze Days', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['team_name'], 'f': '{0} [{1}]'.format(res['team_name'], place) },
                 {'v': res['num_sleaze_days'], 'f': str(int(res['num_sleaze_days']))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/indiv_segment/<int:segment_id>")
def indiv_segment(segment_id):
    
    #an_effort = db.session.query(RideEffort).filter_on(segment_id=segment_id).first() # @UndefinedVariable
    
    q = text ("""
                select A.id, A.name as athlete_name, count(E.id) as segment_rides
                from athletes A
                join rides R on R.athlete_id = A.id
                join ride_efforts E on E.ride_id = R.id
                where E.segment_id = :segment_id
                group by A.id, A.name
                order by segment_rides desc
                ;
            """)
    
    indiv_q = db.engine.execute(q, segment_id=segment_id).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Times Ridden', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) },
                 {'v': res['segment_rides'], 'f': str(int(res['segment_rides']))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/team_segment/<int:segment_id>")
def team_segment(segment_id):
    
    #an_effort = db.session.query(RideEffort).filter_on(segment_id=segment_id).first() # @UndefinedVariable
    
    q = text ("""
                select T.id, T.name as team_name, count(E.id) as segment_rides
                from rides R
                join athletes A on A.id = R.athlete_id
                join teams T on T.id = A.team_id
                join ride_efforts E on E.ride_id = R.id
                where E.segment_id = :segment_id
                group by T.id, T.name
                order by segment_rides desc
                ;
            """)
    
    indiv_q = db.engine.execute(q, segment_id=segment_id).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Team', 'type': 'string'},
            {'id': 'score', 'label': 'Times Ridden', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['team_name'], 'f': '{0} [{1}]'.format(res['team_name'], place) },
                 {'v': res['segment_rides'], 'f': str(int(res['segment_rides']))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})


@blueprint.route("/indiv_avg_speed")
def indiv_avg_speed():
    
    q = text ("""
                select R.athlete_id, A.name as athlete_name, AVG(R.average_speed) as avg_speed
                from rides R
                join athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by avg_speed desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Average Speed', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) },
                 {'v': res['avg_speed'], 'f': "{0:.2f}".format(res['avg_speed'])}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/team_avg_speed")
def team_avg_speed():
    
    q = text ("""
                select T.id, T.name as team_name, AVG(R.average_speed) as avg_speed
                from rides R
                join athletes A on A.id = R.athlete_id
                join teams T on T.id = A.team_id
                group by T.id, T.name
                order by avg_speed desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Team', 'type': 'string'},
            {'id': 'score', 'label': 'Average Speed', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['team_name'], 'f': '{0} [{1}]'.format(res['team_name'], place) },
                 {'v': res['avg_speed'], 'f': "{0:.2f}".format(res['avg_speed'])}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/indiv_freezing")
def indiv_freezing():
    
    q = text ("""
                select R.athlete_id, A.name as athlete_name, sum(R.distance) as distance
                from rides R
                join ride_weather W on W.ride_id = R.id
                join athletes A on A.id = R.athlete_id
                where W.ride_temp_avg < 32
                group by R.athlete_id, athlete_name
                order by distance desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Miles Below Freezing', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) },
                 {'v': res['distance'], 'f': "{0:.2f}".format(res['distance'])}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/indiv_before_sunrise")
def indiv_before_sunrise():
    
    q = text ("""
                select R.athlete_id, A.name as athlete_name,
                sum(time_to_sec(D.before_sunrise)) as dark
                from ride_daylight D
                join rides R on R.id = D.ride_id
                join athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by dark desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'Before Sunrise', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) },
                 {'v': res['dark'], 'f': str(timedelta(seconds=int(res['dark'])))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/indiv_after_sunset")
def indiv_after_sunset():
    
    q = text ("""
                select R.athlete_id, A.name as athlete_name,
                sum(time_to_sec(D.after_sunset)) as dark
                from ride_daylight D
                join rides R on R.id = D.ride_id
                join athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by dark desc
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable
    
    cols = [{'id': 'name', 'label': 'Athlete', 'type': 'string'},
            {'id': 'score', 'label': 'After Sunset', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        cells = [{'v': res['athlete_name'], 'f': '{0} [{1}]'.format(res['athlete_name'], place) },
                 {'v': res['dark'], 'f': str(timedelta(seconds=int(res['dark'])))}]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

        
@blueprint.route("/team_cumul_points")
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

@blueprint.route("/team_cumul_mileage")
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

@blueprint.route("/indiv_elev_dist")
def indiv_elev_dist():
    
    q = text ("""
                select R.athlete_id, A.name as athlete_name,
                T.name as team_name,
                SUM(R.elevation_gain) as total_elevation_gain,
                SUM(R.distance) as total_distance,
                AVG(R.average_speed) as avg_speed
                from rides R
                join athletes A on A.id = R.athlete_id
                left join teams T on T.id = A.team_id
                group by R.athlete_id, athlete_name, team_name
                ;
            """)
    
    indiv_q = db.session.execute(q).fetchall() # @UndefinedVariable

    cols = [{'id': 'ID', 'label': 'ID', 'type': 'string'},
            {'id': 'score', 'label': 'Distance', 'type': 'number'},
            {'id': 'score', 'label': 'Elevation', 'type': 'number'},
            {'id': 'ID', 'label': 'Team', 'type': 'string'},
            {'id': 'score', 'label': 'Average Speed', 'type': 'number'},
            ]
    
    rows = []
    for i,res in enumerate(indiv_q):
        place = i+1
        name_parts = res['athlete_name'].split(' ')
        if len(name_parts) > 1: 
            short_name = ' '.join([name_parts[0], name_parts[-1]])
        else:
            short_name = res['athlete_name']
        
        if res['team_name'] is None:
            team_name = '(No team)'
        else:
            team_name = res['team_name']
            
        cells = [{'v': res['athlete_name'], 'f': short_name },
                 {'v': res['total_distance'], 'f': '{0:.2f}'.format(res['total_distance']) },
                 {'v': res['total_elevation_gain'], 'f': '{0:.2f}'.format(res['total_elevation_gain']) },
                 {'v': team_name, 'f': team_name },
                 {'v': res['avg_speed'], 'f': "{0:.2f}".format(res['avg_speed'])},
                 ]
        rows.append({'c': cells})
        
    return gviz_api_jsonify({'cols': cols, 'rows': rows})

@blueprint.route("/riders_by_lowtemp")
def riders_by_lowtemp():
    """
    """
    q = text("""
            select date(start_date) as start_date,
            avg(W.day_temp_min) as low_temp,
            count(distinct R.athlete_id) as riders 
            from rides R join ride_weather W on W.ride_id = R.id
            group by date(start_date)
            order by date(start_date);
            """)
            
    cols = [{'id': 'date', 'label': 'Date', 'type': 'date'},
            {'id': 'riders', 'label': 'Riders', 'type': 'number'},
            {'id': 'day_temp_min', 'label': 'Low Temp', 'type': 'number'},
            ]
    
    rows = []
    for res in db.session.execute(q): # @UndefinedVariable
        if res['low_temp'] is None:
            # This probably only happens for *today* since that isn't looked up yet.
            continue
        cells = [{'v': res['start_date'] },
                 {'v': res['riders'], 'f': '{0}'.format(res['riders'])},
                 {'v': res['low_temp'], 'f': '{0:.1f}F'.format(res['low_temp'])},
                 ]
        rows.append({'c': cells})

    return gviz_api_jsonify({'cols': cols, 'rows': rows})

def gviz_api_jsonify(*args, **kwargs):
    """
    Override default Flask jsonify to handle JSON for Google Chart API.
    """
    return current_app.response_class(json.dumps(dict(*args, **kwargs),
                                                 indent=None if request.is_xhr else 2, cls=gviz_api.DataTableJSONEncoder),
                                      mimetype='application/json')