"""
Created on Feb 10, 2013

@author: hans
"""

import json
import copy
from collections import defaultdict
from datetime import datetime, timedelta

from flask import current_app, Blueprint, jsonify

from sqlalchemy import text
from dateutil import rrule

from freezing.model import meta
from freezing.model.orm import Team

from freezing.web import config
from freezing.web.utils import gviz_api
from freezing.web.utils.dates import parse_competition_timestamp
from freezing.web.views.shared_sql import *

from pytz import utc

blueprint = Blueprint("chartdata", __name__)


@blueprint.route("/team_leaderboard")
def team_leaderboard_data():
    """
    Loads the leaderboard data broken down by team.
    """
    q = team_leaderboard_query()

    team_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "team_name", "label": "Team", "type": "string"},
        {"id": "score", "label": "Score", "type": "number"},
        # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
    ]

    rows = []
    for i, res in enumerate(team_q):
        place = i + 1
        cells = [
            {"v": res["team_name"], "f": "{0} [{1}]".format(res["team_name"], place)},
            {"v": res["total_score"], "f": str(int(round(res["total_score"])))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/indiv_leaderboard")
def indiv_leaderboard_data():
    """
    Loads the leaderboard data broken down by team.
    """
    q = text(
        """
             select A.id as athlete_id, A.display_name as athlete_name, sum(DS.points) as total_score
             from daily_scores DS
             join lbd_athletes A on A.id = DS.athlete_id
             group by A.id, A.display_name
             order by total_score desc
             ;
             """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Score", "type": "number"},
        # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["total_score"], "f": str(int(round(res["total_score"])))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Score", "type": "number"},
        # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
    ]

    rows = []
    for i, res in enumerate(team_q):
        place = i + 1
        cells = [
            {"v": res["team_name"], "f": "{0} [{1}]".format(res["team_name"], place)},
            {"v": res["cumul_elev_gain"], "f": str(int(res["cumul_elev_gain"]))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Elevation", "type": "number"},
        # {"id":"","label":"","pattern":"","type":"number","p":{"role":"interval"}},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["cumul_elev_gain"], "f": str(int(res["cumul_elev_gain"]))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Moving Time", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {
                "v": res["total_moving_time"],
                "f": str(timedelta(seconds=int(res["total_moving_time"]))),
            },
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Team", "type": "string"},
        {"id": "score", "label": "Moving Time", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {"v": res["team_name"], "f": "{0} [{1}]".format(res["team_name"], place)},
            {
                "v": res["total_moving_time"],
                "f": str(timedelta(seconds=int(res["total_moving_time"]))),
            },
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/indiv_number_sleaze_days")
def indiv_number_sleaze_days():
    q = indiv_sleaze_query()

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Sleaze Days", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["num_sleaze_days"], "f": str(int(res["num_sleaze_days"]))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/team_number_sleaze_days")
def team_number_sleaze_days():
    q = team_sleaze_query()

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Team", "type": "string"},
        {"id": "score", "label": "Sleaze Days", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {"v": res["team_name"], "f": "{0} [{1}]".format(res["team_name"], place)},
            {"v": res["num_sleaze_days"], "f": str(int(res["num_sleaze_days"]))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    indiv_q = meta.engine.execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Kidical Rides", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["kidical_rides"], "f": str(int(res["kidical_rides"]))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/indiv_freeze_points")
def indiv_freeze_points():
    q = indiv_freeze_query()
    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Freeze Points", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {
                "v": res["freeze_points_total"],
                "f": "{0:.2f}".format(res["freeze_points_total"]),
            },
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/indiv_segment/<int:segment_id>")
def indiv_segment(segment_id):
    # an_effort = meta.session_factory().query(RideEffort).filter_on(segment_id=segment_id).first() # @UndefinedVariable

    q = indiv_segment_query()

    indiv_q = meta.engine.execute(
        q, segment_id=segment_id
    ).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Times Ridden", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["segment_rides"], "f": str(int(res["segment_rides"]))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/team_segment/<int:segment_id>")
def team_segment(segment_id):
    # an_effort = meta.session_factory().query(RideEffort).filter_on(segment_id=segment_id).first() # @UndefinedVariable

    q = team_segment_query()

    indiv_q = meta.engine.execute(
        q, segment_id=segment_id
    ).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Team", "type": "string"},
        {"id": "score", "label": "Times Ridden", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {"v": res["team_name"], "f": "{0} [{1}]".format(res["team_name"], place)},
            {"v": res["segment_rides"], "f": str(int(res["segment_rides"]))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Average Speed", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["avg_speed"], "f": "{0:.2f}".format(res["avg_speed"])},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "name", "label": "Team", "type": "string"},
        {"id": "score", "label": "Average Speed", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {"v": res["team_name"], "f": "{0} [{1}]".format(res["team_name"], place)},
            {"v": res["avg_speed"], "f": "{0:.2f}".format(res["avg_speed"])},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Miles Below Freezing", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["distance"], "f": "{0:.2f}".format(res["distance"])},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "Before Sunrise", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["dark"], "f": str(timedelta(seconds=int(res["dark"])))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": "After Sunset", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res["dark"], "f": str(timedelta(seconds=int(res["dark"])))},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/user_daily_points/<athlete_id>")
def user_daily_points(athlete_id):
    """ """
    teams = meta.scoped_session().query(Team).all()  # @UndefinedVariable
    day_q = text(
        """
             select DS.points
             from daily_scores DS
             where DAYOFYEAR(DS.ride_date) = :yday
             and DS.athlete_id = :id
             ;
             """
    )

    cols = [{"id": "day", "label": "Day No.", "type": "string"}]
    cols.append({"id": "athlete_{0}".format(athlete_id), "label": "", "type": "number"})

    # This is a really inefficient way to do this, but it's also super simple.  And I'm feeling lazy :)
    start_date = config.START_DATE
    start_date = start_date.replace(tzinfo=None)
    day_r = rrule.rrule(rrule.DAILY, dtstart=start_date, until=datetime.now())
    rows = []
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
        # these are 1-based, whereas mysql uses 0-based
        cells = [
            {
                "v": "{0}".format(dt.strftime("%b %d")),
                "f": "{0}".format(dt.strftime("%m/%d")),
            },
            # Competition always starts at day 1, regardless of isocalendar day no
        ]

        points = meta.engine.execute(
            day_q, id=athlete_id, yday=day_no
        ).scalar()  # @UndefinedVariable
        if points is None:
            points = 0
        cells.append({"v": points, "f": "{0:.2f}".format(points)})

        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/user_weekly_points/<athlete_id>")
def user_weekly_points(athlete_id):
    """ """
    teams = meta.scoped_session().query(Team).all()  # @UndefinedVariable
    week_q = text(
        """
             select sum(DS.points) as total_score
             from daily_scores DS
             where DS.athlete_id = :athlete_id and week(DS.ride_date) = :week
             ;
             """
    )

    cols = [{"id": "week", "label": "Week No.", "type": "string"}]
    for t in teams:
        cols.append({"id": "team_{0}".format(t.id), "label": t.name, "type": "number"})

    # This is a really inefficient way to do this, but it's also super simple.  And I'm feeling lazy :)
    start_date = config.START_DATE
    start_date = start_date.replace(tzinfo=None)
    week_r = rrule.rrule(rrule.WEEKLY, dtstart=start_date, until=datetime.now())
    rows = []
    for i, dt in enumerate(week_r):
        week_no = dt.date().isocalendar()[1]
        # these are 1-based, whereas mysql uses 0-based
        cells = [
            {"v": "Week {0}".format(i + 1), "f": "Week {0}".format(i + 1)},
            # Competition always starts at week 1, regardless of isocalendar week no
        ]
        for t in teams:
            total_score = meta.engine.execute(
                week_q, athlete_id=athlete_id, week=week_no - 1
            ).scalar()  # @UndefinedVariable
            if total_score is None:
                total_score = 0
            cells.append({"v": total_score, "f": "{0:.2f}".format(total_score)})

        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    weeks = sorted({r["week_num"] for r in res})
    teams = sorted({(r["team_id"], r["team_name"]) for r in res}, key=lambda t: t[1])
    scores = {(r["week_num"], r["team_id"]): r["total_score"] for r in res}

    team_cols = [
        {"id": f"team_{id}", "label": name, "type": "number"} for id, name in teams
    ]
    cols = [{"id": "week", "label": "Week No.", "type": "string"}, *team_cols]

    def week_cells(week: int) -> [dict]:
        def team_cell(id: int) -> dict:
            total_score = scores.get((week, id), 0.0)
            return {"v": total_score, "f": "{0:.2f}".format(total_score)}

        team_cells = [team_cell(id) for id, _ in teams]
        return [{"v": f"Week {week + 1}", "f": f"Week {week + 1}"}, *team_cells]

    rows = [{"c": week_cells(week)} for week in weeks]

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [{"id": "date", "label": "Date", "type": "date"}]

    for team in teams:
        cols.append(
            {"id": "team_{0}".format(team.id), "label": team.name, "type": "number"}
        )

    start_date = config.START_DATE
    start_date = start_date.replace(tzinfo=None)
    tpl_dict = dict(
        [
            (dt.strftime("%Y-%m-%d"), None)
            for dt in rrule.rrule(rrule.DAILY, dtstart=start_date, until=datetime.now())
        ]
    )

    # Query for each team, build this into a multidim array
    daily_cumul = defaultdict(dict)

    for team in teams:
        daily_cumul[team.id] = copy.copy(
            tpl_dict
        )  # Ensure that we have keys for every day (even if there were no rides for that day)
        for row in meta.engine.execute(
            q, team_id=team.id
        ).fetchall():  # @UndefinedVariable
            daily_cumul[team.id][row["ride_date"].strftime("%Y-%m-%d")] = row[
                "cumulative_points"
            ]

        # Fill in any None gaps with the previous non-None value
        prev_value = 0
        for datekey in sorted(tpl_dict.keys()):
            if daily_cumul[team.id][datekey] is None:
                daily_cumul[team.id][datekey] = prev_value
            else:
                prev_value = daily_cumul[team.id][datekey]

    rows = []
    for datekey in sorted(tpl_dict.keys()):
        cells = [{"v": parse_competition_timestamp(datekey).date()}]
        for team in teams:
            cells.append({"v": daily_cumul[team.id][datekey]})
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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

    cols = [{"id": "date", "label": "Date", "type": "date"}]

    for team in teams:
        cols.append(
            {"id": "team_{0}".format(team.id), "label": team.name, "type": "number"}
        )

    start_date = config.START_DATE
    start_date = start_date.replace(tzinfo=None)
    tpl_dict = dict(
        [
            (dt.strftime("%Y-%m-%d"), None)
            for dt in rrule.rrule(rrule.DAILY, dtstart=start_date, until=datetime.now())
        ]
    )

    # Query for each team, build this into a multidim array
    daily_cumul = defaultdict(dict)

    for team in teams:
        daily_cumul[team.id] = copy.copy(
            tpl_dict
        )  # Ensure that we have keys for every day (even if there were no rides for that day)
        for row in meta.engine.execute(
            q, team_id=team.id
        ).fetchall():  # @UndefinedVariable
            daily_cumul[team.id][row["ride_date"].strftime("%Y-%m-%d")] = row[
                "cumulative_distance"
            ]

        # Fill in any None gaps with the previous non-None value
        prev_value = 0
        for datekey in sorted(tpl_dict.keys()):
            if daily_cumul[team.id][datekey] is None:
                daily_cumul[team.id][datekey] = prev_value
            else:
                prev_value = daily_cumul[team.id][datekey]

    rows = []
    for datekey in sorted(tpl_dict.keys()):
        cells = [{"v": parse_competition_timestamp(datekey).date()}]
        for team in teams:
            cells.append({"v": daily_cumul[team.id][datekey]})
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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
                ;
            """
    )

    indiv_q = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    cols = [
        {"id": "ID", "label": "ID", "type": "string"},
        {"id": "score", "label": "Distance", "type": "number"},
        {"id": "score", "label": "Elevation", "type": "number"},
        {"id": "ID", "label": "Team", "type": "string"},
        {"id": "score", "label": "Average Speed", "type": "number"},
    ]

    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        name_parts = res["athlete_name"].split(" ")
        if len(name_parts) > 1:
            short_name = " ".join([name_parts[0], name_parts[-1]])
        else:
            short_name = res["athlete_name"]

        if res["team_name"] is None:
            team_name = "(No team)"
        else:
            team_name = res["team_name"]

        cells = [
            {"v": res["athlete_name"], "f": short_name},
            {"v": res["total_distance"], "f": "{0:.2f}".format(res["total_distance"])},
            {
                "v": res["total_elevation_gain"],
                "f": "{0:.2f}".format(res["total_elevation_gain"]),
            },
            {"v": team_name, "f": team_name},
            {"v": res["avg_speed"], "f": "{0:.2f}".format(res["avg_speed"])},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/riders_by_lowtemp")
def riders_by_lowtemp():
    """ """
    q = text(
        """
            select date(start_date) as start_date,
            avg(W.day_temp_min) as low_temp,
            count(distinct R.athlete_id) as riders
            from rides R join ride_weather W on W.ride_id = R.id
            group by date(start_date)
            order by date(start_date);
            """
    )

    cols = [
        {"id": "date", "label": "Date", "type": "date"},
        {"id": "riders", "label": "Riders", "type": "number"},
        {"id": "day_temp_min", "label": "Low Temp", "type": "number"},
    ]

    rows = []
    for res in meta.scoped_session().execute(q):  # @UndefinedVariable
        if res["low_temp"] is None:
            # This probably only happens for *today* since that isn't looked up yet.
            continue
        cells = [
            {"v": res["start_date"]},
            {"v": res["riders"], "f": "{0}".format(res["riders"])},
            {"v": res["low_temp"], "f": "{0:.1f}F".format(res["low_temp"])},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


@blueprint.route("/distance_by_lowtemp")
def distance_by_lowtemp():
    """ """
    q = text(
        """
            select date(start_date) as start_date,
            avg(W.day_temp_min) as low_temp,
            sum(R.distance) as distance
            from rides R join ride_weather W on W.ride_id = R.id
            group by date(start_date)
            order by date(start_date);
            """
    )

    cols = [
        {"id": "date", "label": "Date", "type": "date"},
        {"id": "distance", "label": "Distance", "type": "number"},
        {"id": "day_temp_min", "label": "Low Temp", "type": "number"},
    ]

    rows = []
    for res in meta.scoped_session().execute(q):  # @UndefinedVariable
        if res["low_temp"] is None:
            # This probably only happens for *today* since that isn't looked up yet.
            continue
        # res['start_date']
        dt = res["start_date"]
        rows.append(
            {
                "date": {"year": dt.year, "month": dt.month, "day": dt.day},
                "distance": res["distance"],
                "low_temp": res["low_temp"],
            }
        )

    return jsonify({"data": rows})


def gviz_api_jsonify(*args, **kwargs):
    """
    Override default Flask jsonify to handle JSON for Google Chart API.
    """
    return current_app.response_class(
        json.dumps(
            dict(*args, **kwargs),
            indent=None,
            cls=gviz_api.DataTableJSONEncoder,
        ),
        mimetype="application/json",
    )


def exec_and_jsonify_query(
    q,
    display_label,
    query_label,
    hover_lambda=lambda res, query_label: str(int(round(res[query_label]))),
):
    cols = [
        {"id": "name", "label": "Athlete", "type": "string"},
        {"id": "score", "label": display_label, "type": "number"},
    ]

    indiv_q = meta.scoped_session().execute(q).fetchall()
    rows = []
    for i, res in enumerate(indiv_q):
        place = i + 1
        cells = [
            {
                "v": res["athlete_name"],
                "f": "{0} [{1}]".format(res["athlete_name"], place),
            },
            {"v": res[query_label], "f": hover_lambda(res, query_label)},
        ]
        rows.append({"c": cells})

    return gviz_api_jsonify({"cols": cols, "rows": rows})


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
            R.start_date as date,
            R.location as loc,
            R.moving_time as moving
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
          group by athlete_name
          order by {1} {3}, moving DESC;
          """.format(
        weath_field, weath_nick, func, desc, superlative_restriction
    )


@blueprint.route("/indiv_coldest")
def indiv_coldest():
    q = text(parameterized_suffering_query("ride_temp_start", "temp_start", func="min"))
    hl = lambda res, ql: "%.2f F for %s on %s in %s" % (
        res["temp_start"],
        fmt_dur(res["moving"]),
        fmt_date(res["date"]),
        res["loc"],
    )
    return exec_and_jsonify_query(q, "Temperature", "temp_start", hover_lambda=hl)


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
    hl = lambda res, ql: "%.2f in for %s on %s in %s" % (
        res["snow"],
        fmt_dur(res["moving"]),
        fmt_date(res["date"]),
        res["loc"],
    )
    return exec_and_jsonify_query(q, "Snowfall", "snow", hover_lambda=hl)


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
    hl = lambda res, ql: "%.2f in for %s on %s in %s" % (
        res["rain"],
        fmt_dur(res["moving"]),
        fmt_date(res["date"]),
        res["loc"],
    )
    return exec_and_jsonify_query(q, "Rainfall", "rain", hover_lambda=hl)
