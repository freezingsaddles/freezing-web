from collections import defaultdict
from itertools import groupby
from statistics import median

from flask import Blueprint, render_template
from freezing.model import meta
from sqlalchemy import text

blueprint = Blueprint("alt_scoring", __name__)


@blueprint.route("/team_riders")
def team_riders():
    q = text(
        """
        select b.name, count(a.athlete_id) as ride_days from daily_scores a join teams b
        on a.team_id = b.id where a.distance > 1 and b.leaderboard_exclude=0 group by a.team_id order by ride_days desc;
        """
    )
    team_riders = [
        (x["name"], x["ride_days"]) for x in meta.scoped_session().execute(q).fetchall()
    ]
    return render_template(
        "alt_scoring/team_riders.html",
        team_riders=team_riders,
    )


@blueprint.route("/team_daily")
def team_daily():
    q = text(
        """select a.ride_date, b.name as team_name, sum(a.points) as team_score from daily_scores a,
        teams b where a.team_id=b.id and b.leaderboard_exclude=0
        group by a.ride_date, b.name order by a.ride_date, team_score;"""
    )
    temp = [
        (x["ride_date"], x["team_name"])
        for x in meta.scoped_session().execute(q).fetchall()
    ]
    temp = groupby(temp, lambda x: x[0])
    team_daily = defaultdict(list)
    team_total = defaultdict(int)
    for date, team in temp:
        score_list = enumerate([x[1] for x in team], 1)
        for a, b in score_list:
            if not team_daily.get(date):
                team_daily[date] = {}
            team_daily[date].update({a: b})
            if not team_total.get(b):
                team_total[b] = 0
            team_total[b] += a
    team_daily = [(a, b) for a, b in team_daily.items()]
    team_daily = sorted(team_daily)
    # NOTE: team_daily calculated to show the scores for each day
    # chart is too big to display, but leaving the calculation here just in case
    team_total = [(b, a) for a, b in team_total.items()]
    team_total = sorted(team_total, reverse=True)
    return render_template(
        "alt_scoring/team_daily.html",
        team_total=team_total,
    )


@blueprint.route("/indiv_worst_day_points")
def indiv_worst_day_points():
    ridersq = text(
        """
    select count(distinct(athlete_id)) as riders from rides group by date(start_date)
    """
    )
    riders = [x["riders"] for x in meta.scoped_session().execute(ridersq).fetchall()]
    median_riders = 0 if len(riders) == 0 else median(riders)
    q = text(
        f"""
    select A.id as athlete_id, A.team_id, A.display_name as athlete_name, T.name as team_name,
    sum(s.distance) as total_distance, sum(s.points) as total_score, sum(s.adj_points) as total_adjusted,
    count(s.points) as days_ridden from
    (select DS.athlete_id, DS.distance, DS.points, DS.ride_date, DDS.num_riders, (DS.points*POW(1.025,({median_riders}-DDS.num_riders))) adj_points from daily_scores DS,
    (select ride_date, count(distinct(athlete_id)) as num_riders  from daily_scores group by ride_date order by ride_date) DDS where DS.ride_date=DDS.ride_date) s
    join lbd_athletes A on A.id = s.athlete_id
    join teams T on T.id = A.team_id
    group by A.id, A.display_name
    order by total_adjusted desc;
    """  # nosec B608
    )
    data = [
        (
            x["athlete_id"],
            x["athlete_name"],
            x["team_name"],
            x["total_distance"],
            x["total_score"],
            x["total_adjusted"],
            x["days_ridden"],
        )
        for x in meta.scoped_session().execute(q).fetchall()
    ]
    return render_template(
        "alt_scoring/indiv_worst_day_points.html",
        data=data,
        median=median_riders,
    )
