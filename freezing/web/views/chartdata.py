"""
Created on Feb 10, 2013

@author: hans
"""

import copy
from collections import defaultdict
from datetime import datetime, timedelta

from dateutil import rrule
from flask import Blueprint, jsonify
from freezing.model import meta
from freezing.model.orm import Team
from pytz import utc
from sqlalchemy import text

from freezing.web import config
from freezing.web.views.shared_sql import (
    indiv_freeze_query,
    indiv_segment_query,
    indiv_sleaze_query,
    team_leaderboard_query,
    team_segment_query,
    team_sleaze_query,
)

blueprint = Blueprint("chartdata", __name__)


@blueprint.route("/team_leaderboard")
def team_leaderboard_data():
    """
    Loads the leaderboard data broken down by team.
    """
    q = team_leaderboard_query()

    team_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    values = []
    ranks = []
    for i, res in enumerate(team_q):
        values.append(res._mapping["total_score"])
        labels.append(res._mapping["team_name"])
        ranks.append(res._mapping["rank"])

    return jsonify({"labels": labels, "values": values, "ranks": ranks})


@blueprint.route("/indiv_leaderboard")
def indiv_leaderboard_data():
    """
    Loads the leaderboard data broken down by team.
    """
    q = text(
        """
             select
               A.id as athlete_id,
               A.display_name as athlete_name,
               sum(DS.points) as total_score,
               rank() over (order by sum(DS.points) desc) as "rank"
             from daily_scores DS
             join lbd_athletes A on A.id = DS.athlete_id
             group by A.id, A.display_name
             order by total_score desc
             ;
             """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    values = []
    ranks = []
    for i, res in enumerate(indiv_q):
        values.append(res._mapping["total_score"])
        labels.append(res._mapping["athlete_name"])
        ranks.append(res._mapping["rank"])

    return jsonify({"labels": labels, "values": values, "ranks": ranks})


@blueprint.route("/team_elev_gain")
def team_elev_gain():
    q = text(
        """
        select T.id, T.name as team_name, sum(R.elevation_gain) as cumul_elev_gain
        from rides R
        join lbd_athletes A on A.id = R.athlete_id
        join teams T on T.id = A.team_id
        group by T.id, team_name
        order by cumul_elev_gain desc
        ;
        """
    )

    team_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(team_q):
        ranks.append(i + 1)
        labels.append(res._mapping["team_name"])
        values.append(res._mapping["cumul_elev_gain"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "elevation gain",
            "suffix": " ft",
            "unit": "feet",
        }
    )


@blueprint.route("/indiv_elev_gain")
def indiv_elev_gain():
    q = text(
        """
                select R.athlete_id, A.display_name as athlete_name, sum(R.elevation_gain) as cumul_elev_gain
                from rides R
                join lbd_athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by cumul_elev_gain desc
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["cumul_elev_gain"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "elevation gain",
            "suffix": " ft",
            "unit": "feet",
        }
    )


@blueprint.route("/indiv_moving_time")
def indiv_moving_time():
    q = text(
        """
                select R.athlete_id, A.display_name as athlete_name, sum(R.moving_time) as total_moving_time
                from rides R
                join lbd_athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by total_moving_time desc
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []
    tooltips = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["total_moving_time"] / 60)
        tooltips.append(str(timedelta(seconds=int(res._mapping["total_moving_time"]))))

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "tooltips": tooltips,
            "key": "total moving time",
            "unit": "minutes",
        }
    )


@blueprint.route("/team_moving_time")
def team_moving_time():
    q = text(
        """
                select T.id, T.name as team_name, sum(R.moving_time) as total_moving_time
                from rides R
                join lbd_athletes A on A.id = R.athlete_id
                join teams T on T.id = A.team_id
                group by T.id, T.name
                order by total_moving_time desc
                ;
            """
    )

    team_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []
    tooltips = []

    for i, res in enumerate(team_q):
        ranks.append(i + 1)
        labels.append(res._mapping["team_name"])
        values.append(res._mapping["total_moving_time"] / 60)
        tooltips.append(str(timedelta(seconds=int(res._mapping["total_moving_time"]))))

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "tooltips": tooltips,
            "key": "total moving time",
            "unit": "minutes",
        }
    )


@blueprint.route("/indiv_number_sleaze_days")
def indiv_number_sleaze_days():
    q = indiv_sleaze_query()

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["num_sleaze_days"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "sleaze days",
            "suffix": "",
            "unit": "days",
        }
    )


@blueprint.route("/team_number_sleaze_days")
def team_number_sleaze_days():
    q = team_sleaze_query()

    team_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(team_q):
        ranks.append(i + 1)
        labels.append(res._mapping["team_name"])
        values.append(res._mapping["num_sleaze_days"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "sleaze days",
            "suffix": "",
            "unit": "days",
        }
    )


@blueprint.route("/indiv_kidical")
def indiv_kidical():
    # an_effort = meta.session_factory().query(RideEffort).filter_on(segment_id=segment_id).first() # @UndefinedVariable

    q = text(
        """
                select A.id, A.display_name as athlete_name, count(R.id) as kidical_rides
                from lbd_athletes A
                join rides R on R.athlete_id = A.id
                where R.name like '%#kidical%'
                group by A.id, A.display_name
                order by kidical_rides desc
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["kidical_rides"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "kidical rides",
            "suffix": "",
            "unit": "rides",
        }
    )


@blueprint.route("/indiv_freeze_points")
def indiv_freeze_points():
    q = indiv_freeze_query()
    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["freeze_points_total"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "points",
            "suffix": "",
            "unit": "Freeze Points",
        }
    )


@blueprint.route("/indiv_segment/<int:segment_id>")
def indiv_segment(segment_id):
    # an_effort = meta.session_factory().query(RideEffort).filter_on(segment_id=segment_id).first() # @UndefinedVariable

    q = indiv_segment_query().bindparams(segment_id=segment_id)

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["segment_rides"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "rides",
            "suffix": "",
            "unit": "",
        }
    )


@blueprint.route("/team_segment/<int:segment_id>")
def team_segment(segment_id):
    # an_effort = meta.session_factory().query(RideEffort).filter_on(segment_id=segment_id).first() # @UndefinedVariable

    q = team_segment_query().bindparams(segment_id=segment_id)

    team_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(team_q):
        ranks.append(i + 1)
        labels.append(res._mapping["team_name"])
        values.append(res._mapping["segment_rides"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "rides",
            "suffix": "",
            "unit": "",
        }
    )


@blueprint.route("/indiv_avg_speed")
def indiv_avg_speed():
    q = text(
        """
                select R.athlete_id, A.display_name as athlete_name, SUM(R.distance) / (SUM(R.moving_time) / 3600) as avg_speed
                from rides R
                join lbd_athletes A on A.id = R.athlete_id
                where R.manual = false
                group by R.athlete_id, athlete_name
                order by avg_speed desc
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["avg_speed"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "average speed",
            "suffix": " mph",
            "unit": "mph",
            "precision": 1,
        }
    )


@blueprint.route("/team_avg_speed")
def team_avg_speed():
    q = text(
        """
                select T.id, T.name as team_name, SUM(R.distance) / (SUM(R.moving_time) / 3600) as avg_speed
                from rides R
                join lbd_athletes A on A.id = R.athlete_id
                join teams T on T.id = A.team_id
                where R.manual = false
                group by T.id, T.name
                order by avg_speed desc
                ;
            """
    )

    team_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(team_q):
        ranks.append(i + 1)
        labels.append(res._mapping["team_name"])
        values.append(res._mapping["avg_speed"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "average speed",
            "suffix": " mph",
            "unit": "mph",
            "precision": 1,
        }
    )


@blueprint.route("/indiv_freezing")
def indiv_freezing():
    q = text(
        """
                select R.athlete_id, A.display_name as athlete_name, sum(R.distance) as distance
                from rides R
                join ride_weather W on W.ride_id = R.id
                join lbd_athletes A on A.id = R.athlete_id
                where W.ride_temp_avg < 32
                group by R.athlete_id, athlete_name
                order by distance desc
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["distance"])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": "distance",
            "suffix": " mi",
            "unit": "miles",
            "precision": 1,
        }
    )


@blueprint.route("/indiv_before_sunrise")
def indiv_before_sunrise():
    q = text(
        """
                select R.athlete_id, A.display_name as athlete_name,
                sum(time_to_sec(D.before_sunrise)) as dark
                from ride_daylight D
                join rides R on R.id = D.ride_id
                join lbd_athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by dark desc
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []
    tooltips = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["dark"])
        tooltips.append(str(timedelta(seconds=int(res._mapping["dark"]))))

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "tooltips": tooltips,
            "key": "time",
            "unit": "minutes",
        }
    )


@blueprint.route("/indiv_after_sunset")
def indiv_after_sunset():
    q = text(
        """
                select R.athlete_id, A.display_name as athlete_name,
                sum(time_to_sec(D.after_sunset)) as dark
                from ride_daylight D
                join rides R on R.id = D.ride_id
                join lbd_athletes A on A.id = R.athlete_id
                group by R.athlete_id, athlete_name
                order by dark desc
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    labels = []
    ranks = []
    values = []
    tooltips = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping["dark"])
        tooltips.append(str(timedelta(seconds=int(res._mapping["dark"]))))

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "tooltips": tooltips,
            "key": "time",
            "unit": "minutes",
        }
    )


def competition_start():
    start_date = config.START_DATE
    return start_date.replace(
        hour=12, tzinfo=None
    )  # mid-day to avoid the tyranny of timezones


def now_or_competition_end():
    end_date = config.END_DATE
    return min(datetime.now(), end_date.replace(hour=12, tzinfo=None))


@blueprint.route("/user_daily_points/<athlete_id>")
def user_daily_points(athlete_id):
    """ """
    day_q = text(
        """
             select DS.points
             from daily_scores DS
             where DAYOFYEAR(DS.ride_date) = :yday
             and DS.athlete_id = :id
             ;
             """
    )

    # This is a really inefficient way to do this, but it's also super simple.  And I'm feeling lazy :)
    day_r = rrule.rrule(
        rrule.DAILY, dtstart=competition_start(), until=now_or_competition_end()
    )
    days = []
    points = []
    for i, dt in enumerate(day_r):
        # Thanks Stack Overflow https://stackoverflow.com/a/25265611/424301
        day_no = (
            utc.localize(
                dt,
                is_dst=None,
            )
            .astimezone(config.TIMEZONE)
            .timetuple()
            .tm_yday
        )
        pts = (
            meta.scoped_session()
            .execute(day_q.bindparams(id=athlete_id, yday=day_no))
            .scalar()
        )  # @UndefinedVariable
        days.append(dt.isoformat())
        points.append(0 if pts is None else pts)

    return jsonify({"days": days, "points": points})


@blueprint.route("/user_weekly_points/<athlete_id>")
def user_weekly_points(athlete_id):
    """ """
    week_q = text(
        """
             select sum(DS.points) as total_score
             from daily_scores DS
             where DS.athlete_id = :athlete_id and week(DS.ride_date) = :week
             ;
             """
    )

    # Slow garbage.
    # This is a really inefficient way to do this, but it's also super simple.  And I'm feeling lazy :)
    week_r = rrule.rrule(
        rrule.WEEKLY, dtstart=competition_start(), until=now_or_competition_end()
    )
    weeks = []
    points = []
    for i, dt in enumerate(week_r):
        week_no = dt.date().isocalendar()[1]

        total_score = (
            meta.scoped_session()
            .execute(week_q.bindparams(athlete_id=athlete_id, week=week_no - 1))
            .scalar()
        )  # @UndefinedVariable
        weeks.append(i + 1)
        points.append(0 if total_score is None else total_score)

    return jsonify({"weeks": weeks, "points": points})


@blueprint.route("/team_weekly_points")
def team_weekly_points():
    """ """

    q = text(
        """
             select
               DS.team_id as team_id,
               T.name as team_name,
               sum(DS.points) as total_score,
               week(DS.ride_date) as week_num
             from
               daily_scores DS inner join
               teams T on T.id = DS.team_id
             where
               not T.leaderboard_exclude
             group by
               team_id,
               week_num
             ;
             """
    )

    res = meta.scoped_session().execute(q).fetchall()

    weeks = sorted({r._mapping["week_num"] for r in res})
    teams = sorted(
        {(r._mapping["team_id"], r._mapping["team_name"]) for r in res},
        key=lambda t: t[1],
    )
    scores = {
        (r._mapping["week_num"], r._mapping["team_id"]): r._mapping["total_score"]
        for r in res
    }

    response = {}
    response["x"] = ["x"] + [week + 1 for week in weeks]
    response["teams"] = [name for id, name in teams]
    for id, name in teams:
        response[name] = [name] + [scores.get((week, id), 0.0) for week in weeks]

    return jsonify(response)


@blueprint.route("/team_cumul_points")
def team_cumul_points():
    """ """
    teams = meta.scoped_session().query(Team).all()  # @UndefinedVariable

    q = text(
        """
            select team_id, ride_date, points,
                     (@total_points := @total_points + points) AS cumulative_points,
                     (@total_distance := @total_distance + points) AS cumulative_distance
             from daily_scores, (select @total_points := 0, @total_distance := 0) AS vars
             where team_id = :team_id
             order by ride_date;
             """
    )

    dates = [
        dt.strftime("%Y-%m-%d")
        for dt in rrule.rrule(
            rrule.DAILY, dtstart=competition_start(), until=now_or_competition_end()
        )
    ]
    tpl_dict = dict([(dt, None) for dt in dates])

    # Query for each team, build this into a multidim array
    daily_cumul = defaultdict(dict)

    for team in teams:
        daily_cumul[team.id] = copy.copy(
            tpl_dict
        )  # Ensure that we have keys for every day (even if there were no rides for that day)
        for row in (
            meta.scoped_session().execute(q.bindparams(team_id=team.id)).fetchall()
        ):  # @UndefinedVariable
            daily_cumul[team.id][row._mapping["ride_date"].strftime("%Y-%m-%d")] = (
                row._mapping["cumulative_points"]
            )

        # Fill in any None gaps with the previous non-None value
        prev_value = 0
        for datekey in dates:
            if daily_cumul[team.id][datekey] is None:
                daily_cumul[team.id][datekey] = prev_value
            else:
                prev_value = daily_cumul[team.id][datekey]

    response = {}
    response["dates"] = ["date"] + dates
    response["teams"] = [team.name for team in teams]
    for team in teams:
        response[team.name] = [team.name] + [
            daily_cumul[team.id][date] for date in dates
        ]

    return jsonify(response)


@blueprint.route("/team_cumul_mileage")
def team_cumul_mileage():
    """ """
    teams = meta.scoped_session().query(Team).all()  # @UndefinedVariable

    q = text(
        """
            select team_id, ride_date, points,
                     (@total_points := @total_points + points) AS cumulative_points,
                     (@total_distance := @total_distance + points) AS cumulative_distance
             from daily_scores, (select @total_points := 0, @total_distance := 0) AS vars
             where team_id = :team_id
             order by ride_date;
             """
    )

    dates = [
        dt.strftime("%Y-%m-%d")
        for dt in rrule.rrule(
            rrule.DAILY, dtstart=competition_start(), until=now_or_competition_end()
        )
    ]
    tpl_dict = dict([(dt, None) for dt in dates])

    # Query for each team, build this into a multidim array
    daily_cumul = defaultdict(dict)

    for team in teams:
        daily_cumul[team.id] = copy.copy(
            tpl_dict
        )  # Ensure that we have keys for every day (even if there were no rides for that day)
        for row in (
            meta.scoped_session().execute(q.bindparams(team_id=team.id)).fetchall()
        ):  # @UndefinedVariable
            daily_cumul[team.id][row._mapping["ride_date"].strftime("%Y-%m-%d")] = (
                row._mapping["cumulative_distance"]
            )

        # Fill in any None gaps with the previous non-None value
        prev_value = 0
        for datekey in dates:
            if daily_cumul[team.id][datekey] is None:
                daily_cumul[team.id][datekey] = prev_value
            else:
                prev_value = daily_cumul[team.id][datekey]

    response = {}
    response["dates"] = ["date"] + dates
    response["teams"] = [team.name for team in teams]
    for team in teams:
        response[team.name] = [team.name] + [
            daily_cumul[team.id][date] for date in dates
        ]

    return jsonify(response)


@blueprint.route("/indiv_elev_dist")
def indiv_elev_dist():
    q = text(
        """
                select R.athlete_id, A.display_name as athlete_name,
                T.name as team_name,
                SUM(R.elevation_gain) as total_elevation_gain,
                SUM(R.distance) as total_distance,
                SUM(R.distance) / (SUM(R.moving_time) / 3600) as avg_speed
                from rides R
                join lbd_athletes A on A.id = R.athlete_id
                left join teams T on T.id = A.team_id
                where not R.manual
                group by R.athlete_id, athlete_name, team_name
                order by SUM(R.distance)
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    athletes = []
    teams = []
    elevations = []
    distances = []
    speeds = []
    for i, res in enumerate(indiv_q):
        athletes.append(res._mapping["athlete_name"])
        teams.append(res._mapping["team_name"])
        elevations.append(int(res._mapping["total_elevation_gain"]))
        distances.append(res._mapping["total_distance"])
        speeds.append(res._mapping["avg_speed"])

    return jsonify(
        {
            "athletes": athletes,
            "teams": teams,
            "elevations": elevations,
            "distances": distances,
            "speeds": speeds,
        }
    )


@blueprint.route("/riders_by_lowtemp")
def riders_by_lowtemp():
    """
    Snowiness and raininess are in the average inches per hour of snowfall during rides.
    A better metric would probably be total rain/snow at DCA on the day, but this is the measure we have.
    """
    q = text(
        """
            select date(start_date) as start_date,
            avg(W.day_temp_min) as low_temp,
            avg(W.ride_windchill_avg) as wind_chill,
            cast(sum(W.ride_rain) * 3600 / sum(R.moving_time) as float) as raininess,
            cast(sum(W.ride_snow) * 3600 / sum(R.moving_time) as float) as snowiness,
            count(distinct R.athlete_id) as riders
            from rides R join ride_weather W on W.ride_id = R.id
            group by date(start_date)
            order by date(start_date);
            """
    )

    rows = []
    for res in meta.scoped_session().execute(q):  # @UndefinedVariable
        if res._mapping["low_temp"] is None:
            # This probably only happens for *today* since that isn't looked up yet.
            continue
        # res['start_date']
        dt = res._mapping["start_date"]

        rows.append(
            {
                "date": {"year": dt.year, "month": dt.month, "day": dt.day},
                "riders": res._mapping["riders"],
                "low_temp": res._mapping["low_temp"],
                "wind_chill": res._mapping["wind_chill"],
                "raininess": res._mapping["raininess"],
                "snowiness": res._mapping["snowiness"],
            }
        )

    return jsonify({"data": rows})


@blueprint.route("/distance_by_lowtemp")
def distance_by_lowtemp():
    """ """
    q = text(
        """
            select date(start_date) as start_date,
            avg(W.day_temp_min) as low_temp,
            avg(W.ride_windchill_avg) as wind_chill,
            cast(sum(W.ride_rain) * 3600 / sum(R.moving_time) as float) as raininess,
            cast(sum(W.ride_snow) * 3600 / sum(R.moving_time) as float) as snowiness,
            sum(R.distance) as distance
            from rides R join ride_weather W on W.ride_id = R.id
            group by date(start_date)
            order by date(start_date);
            """
    )

    rows = []
    for res in meta.scoped_session().execute(q):  # @UndefinedVariable
        if res._mapping["low_temp"] is None:
            # This probably only happens for *today* since that isn't looked up yet.
            continue
        # res['start_date']
        dt = res._mapping["start_date"]
        rows.append(
            {
                "date": {"year": dt.year, "month": dt.month, "day": dt.day},
                "distance": res._mapping["distance"],
                "low_temp": res._mapping["low_temp"],
                "wind_chill": res._mapping["wind_chill"],
                "raininess": res._mapping["raininess"],
                "snowiness": res._mapping["snowiness"],
            }
        )

    return jsonify({"data": rows})


def short(name, max_len=17):
    if len(name) < max_len:
        return name
    else:
        return "{}…{}".format(name[: max_len - 2], name[len(name) - 1 : len(name)])


def exec_and_jsonify_query(
    q,
    display_label,
    query_label,
    suffix,
    hover_lambda=lambda res, query_label: str(int(round(res[query_label]))),
):
    indiv_q = meta.scoped_session().execute(q).fetchall()

    labels = []
    ranks = []
    values = []

    for i, res in enumerate(indiv_q):
        ranks.append(i + 1)
        labels.append(res._mapping["athlete_name"])
        values.append(res._mapping[query_label])

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "ranks": ranks,
            "key": query_label,
            "suffix": suffix,
            "unit": display_label,
            "precision": 1,
        }
    )


def fmt_date(dt):
    return dt.strftime("%Y-%m-%d")


def fmt_dur(elapsed_sec):
    td = timedelta(seconds=elapsed_sec)
    return str(td)


def fmt_if_safe(fmt, val):
    if val:
        return fmt % val
    return ""


def parameterized_suffering_query(
    weath_field, weath_nick, func="min", desc="", superlative_restriction="true"
):
    return """
         select A.display_name as athlete_name,
         A.id as ath_id,
            W.{0} as {1},
            any_value(R.start_date) as date,
            any_value(R.location) as loc,
            any_value(R.moving_time) as moving
            from rides R
            inner join ride_weather W on R.id=W.ride_id
            inner join lbd_athletes A on A.id=R.athlete_id
            inner join (
              select A2.id as ath2_id,
                  {2}({0}) as {1}2
              from rides R2
              inner join ride_weather W2 on R2.id=W2.ride_id
              inner join lbd_athletes A2 on A2.id=R2.athlete_id
              where {4}
              group by A2.id
             ) as SQ
           ON SQ.{1}2 = W.{0}
           AND SQ.ath2_id = A.id
          group by athlete_name, ath_id
          order by {1} {3}, moving DESC;
          """.format(  # nosec B608
        weath_field, weath_nick, func, desc, superlative_restriction
    )


@blueprint.route("/indiv_coldest")
def indiv_coldest():
    q = text(parameterized_suffering_query("ride_temp_start", "temp_start", func="min"))

    def hl(res, ql):
        "%.2f F for %s on %s in %s" % (
            res._mapping["temp_start"],
            fmt_dur(res._mapping["moving"]),
            fmt_date(res._mapping["date"]),
            res._mapping["loc"],
        )

    return exec_and_jsonify_query(q, "", "temp_start", "º F", hover_lambda=hl)


@blueprint.route("/indiv_snowiest")
def indiv_snowiest():
    q = text(
        parameterized_suffering_query(
            "ride_precip",
            "snow",
            func="max",
            desc="desc",
            superlative_restriction="W2.ride_snow=1",
        )
    )

    def hl(res, ql):
        "%.2f in for %s on %s in %s" % (
            res._mapping["snow"],
            fmt_dur(res._mapping["moving"]),
            fmt_date(res._mapping["date"]),
            res._mapping["loc"],
        )

    return exec_and_jsonify_query(q, "Snowfall", "snow", '"', hover_lambda=hl)


@blueprint.route("/indiv_rainiest")
def indiv_rainiest():
    q = text(
        parameterized_suffering_query(
            "ride_precip",
            "rain",
            func="max",
            desc="desc",
            superlative_restriction="W2.ride_rain=1",
        )
    )

    def hl(res, ql):
        "%.2f in for %s on %s in %s" % (
            res._mapping["rain"],
            fmt_dur(res._mapping["moving"]),
            fmt_date(res._mapping["date"]),
            res._mapping["loc"],
        )

    return exec_and_jsonify_query(q, "Rainfall", "rain", '"', hover_lambda=hl)
