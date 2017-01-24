from collections import defaultdict
from itertools import groupby

from flask import render_template, Blueprint
from sqlalchemy import text

from bafs import db
from bafs.views.shared_sql import *


blueprint = Blueprint('alt_scoring', __name__)


@blueprint.route("/team_riders")
def team_riders():
    q = text("""
		select b.name, count(a.athlete_id) as ride_days from daily_scores a join teams b
		on a.team_id = b.id where a.distance > 1 and b.leaderboard_exclude=0 group by a.team_id order by ride_days desc;
		"""
    )
    team_riders = [(x['name'], x['ride_days']) for x in db.session.execute(q).fetchall()]
    return render_template('alt_scoring/team_riders.html', team_riders=team_riders)


@blueprint.route("/team_daily")
def team_daily():
    q = text("""select a.ride_date, b.name as team_name, sum(a.points) as team_score from daily_scores a,
        teams b where a.team_id=b.id and b.leaderboard_exclude=0
        group by a.ride_date, b.name order by a.ride_date, team_score;"""
    )
    temp = [(x['ride_date'], x['team_name']) for x in db.session.execute(q).fetchall()]
    temp = groupby(temp, lambda x:x[0])
    team_daily = defaultdict(list)
    team_total = defaultdict(int)
    for date, team in temp:
        score_list = enumerate([x[1] for x in team], 1)
        for a,b in score_list:
            if not team_daily.get(date):
                team_daily[date] = {}
            team_daily[date].update({a:b})
            if not team_total.get(b):
                team_total[b] = 0
            team_total[b] += (a)
    team_daily = [(a,b) for a,b in team_daily.iteritems()]
    team_daily = sorted(team_daily)
    #NOTE: team_daily calculated to show the scores for each day
    # chart is too big to display, but leaving the calculation here just in case
    team_total = [(b,a) for a,b in team_total.iteritems()]
    team_total = sorted(team_total, reverse = True)
    return render_template('alt_scoring/team_daily.html', team_total=team_total)

@blueprint.route("/team_sleaze")
def team_sleaze():
    q = team_sleaze_query()
    data = [(x['team_name'], x['num_sleaze_days']) for x in db.session.execute(q).fetchall()]
    return render_template('alt_scoring/team_sleaze.html', team_sleaze=data)

@blueprint.route("/team_hains")
def team_hains():
    q = team_segment_query()
    data = [(x['team_name'], x['segment_rides']) for x in db.engine.execute(q,segment_id=1081507).fetchall()]
    return render_template('alt_scoring/team_hains.html', team_hains=data)

@blueprint.route("/indiv_sleaze")
def indiv_sleaze():
    q = indiv_sleaze_query()
    data = [(x['athlete_name'], x['num_sleaze_days']) for x in db.session.execute(q).fetchall()]
    return render_template('alt_scoring/indiv_sleaze.html', indiv_sleaze=data)

@blueprint.route("/indiv_hains")
def indiv_hains():
    q = indiv_segment_query(join_miles=True)
    data = [(x['athlete_name'], x['segment_rides'], x['dist']) for x in db.engine.execute(q,segment_id=1081507).fetchall()]
    return render_template('alt_scoring/indiv_hains.html', indiv_hains=data)

@blueprint.route("/indiv_freeze")
def indiv_freeze():
    q = indiv_freeze_query()
    data = [(x['athlete_name'], x['freeze_points_total']) for x in db.session.execute(q).fetchall()]
    return render_template('alt_scoring/indiv_freeze.html', indiv_freeze=data)

@blueprint.route("/indiv_worst_day_points")
def indiv_worst_day_points():
    q = text("""
    select A.id as athlete_id, A.team_id, A.display_name as athlete_name, T.name as team_name,
    sum(s.distance) as total_distance, sum(s.points) as total_score, sum(s.adj_points) as total_adjusted,
    count(s.points) as days_ridden from
    (select DS.athlete_id, DS.distance, DS.points, DS.ride_date, DDS.num_riders, (DS.points*POW(1.025,(200-DDS.num_riders))) adj_points from daily_scores DS,
    (select ride_date, count(distinct(athlete_id)) as num_riders  from daily_scores group by ride_date order by ride_date) DDS where DS.ride_date=DDS.ride_date) s
    join athletes A on A.id = s.athlete_id
    join teams T on T.id = A.team_id
    group by A.id, A.display_name
    order by total_adjusted desc;
    """)
    data = [(x['athlete_name'], x['team_name'], x['total_distance'], x['total_score'], x['total_adjusted'], x['days_ridden']) for x in db.session.execute(q).fetchall()]
    return render_template('alt_scoring/indiv_worst_day_points.html', data=data)
