from collections import defaultdict
from itertools import groupby

from flask import render_template, Blueprint
from sqlalchemy import text

from bafs import db


blueprint = Blueprint('alt_scoring', __name__)


@blueprint.route("/team_riders")
def team_riders():
    q = text("""
		select b.name, count(a.athlete_id) as ride_days from daily_scores a join teams b
		on a.team_id = b.id where a.distance > 1 group by a.team_id order by ride_days desc;
		"""
    )
    team_riders = [(x['name'], x['ride_days']) for x in db.session.execute(q).fetchall()]
    return render_template('alt_scoring/team_riders.html', team_riders=team_riders)


@blueprint.route("/team_daily")
def team_daily():
    q = text("""select a.ride_date, b.name as team_name, sum(a.points) as team_score from daily_scores a,
        teams b where a.team_id=b.id
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