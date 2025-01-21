from flask import Blueprint, render_template, request, session, url_for
from freezing.model import meta
from sqlalchemy import text
from werkzeug.utils import redirect

from freezing.web import config
from freezing.web.views.shared_sql import (
    indiv_freeze_query,
    indiv_segment_query,
    indiv_sleaze_query,
    team_leaderboard_query,
    team_segment_query,
    team_sleaze_query,
)

blueprint = Blueprint("leaderboard", __name__)


@blueprint.route("/")
def leaderboard():
    return redirect(url_for(".team_leaderboard"))


@blueprint.route("/team")
def team_leaderboard():
    return render_template(
        "leaderboard/team.html",
    )


@blueprint.route("/team_text")
def team_leaderboard_classic():
    athlete_id = session.get("athlete_id")

    # Get teams sorted by points
    q = team_leaderboard_query()

    # @UndefinedVariable
    team_rows = meta.scoped_session().execute(q).fetchall()

    q = text(
        """
             select
               A.id as athlete_id,
               A.team_id,
               A.display_name as athlete_name,
               sum(DS.points) as total_score,
               sum(DS.distance) as total_distance,
               count(DS.points) as days_ridden
             from
               daily_scores DS join athletes A on A.id = DS.athlete_id
             group by A.id, A.display_name
             order by total_score desc
             ;
             """
    )

    team_members = {}
    # @UndefinedVariable
    for indiv_row in meta.scoped_session().execute(q).fetchall():
        team_members.setdefault(indiv_row["team_id"], []).append(indiv_row)

    my_team = next(
        (
            team_id
            for team_id in team_members
            if any(
                member["athlete_id"] == athlete_id for member in team_members[team_id]
            )
        ),
        None,
    )

    for team_id in team_members:
        team_members[team_id] = reversed(
            sorted(team_members[team_id], key=lambda m: m["total_score"])
        )

    return render_template(
        "leaderboard/team_text.html",
        team_rows=team_rows,
        team_members=team_members,
        my_team=my_team,
    )


@blueprint.route("/team_various")
def team_leaderboard_various():
    return render_template(
        "leaderboard/team_various.html",
    )


@blueprint.route("/individual")
def indiv_leaderboard():
    return render_template(
        "leaderboard/indiv.html",
    )


@blueprint.route("/individual_text")
def individual_leaderboard_text():
    athlete_id = session.get("athlete_id")

    q = text(
        """
             select
               A.id as athlete_id,
               A.team_id,
               A.display_name as athlete_name,
               T.name as team_name,
               sum(DS.distance) as total_distance,
               sum(DS.points) as total_score,
               count(DS.points) as days_ridden
             from
               daily_scores DS
                 join lbd_athletes A on A.id = DS.athlete_id
                 join teams T on T.id = A.team_id
             where not T.leaderboard_exclude
             group by A.id, A.display_name
             order by total_score desc
             ;
             """
    )

    # @UndefinedVariable
    indiv_rows = meta.scoped_session().execute(q).fetchall()

    return render_template(
        "leaderboard/indiv_text.html",
        indiv_rows=indiv_rows,
        myself=athlete_id,
    )


@blueprint.route("/individual_various")
def indiv_leaderboard_various():
    return render_template(
        "leaderboard/indiv_various.html",
    )


@blueprint.route("/team_sleaze")
def team_sleaze():
    q = team_sleaze_query()
    data = [
        (x["team_name"], x["num_sleaze_days"])
        for x in meta.scoped_session().execute(q).fetchall()
    ]
    return render_template(
        "alt_scoring/team_sleaze.html",
        team_sleaze=data,
        competition_title=config.COMPETITION_TITLE,
        registration_site=config.REGISTRATION_SITE,
    )


@blueprint.route("/team_hains")
def team_hains():
    q = team_segment_query()
    data = [
        (x["team_name"], x["segment_rides"])
        for x in meta.engine.execute(q, segment_id=1081507).fetchall()
    ]
    return render_template(
        "alt_scoring/team_hains.html",
        team_hains=data,
    )


@blueprint.route("/indiv_sleaze")
def indiv_sleaze():
    q = indiv_sleaze_query()
    data = [
        (x["athlete_name"], x["num_sleaze_days"])
        for x in meta.scoped_session().execute(q).fetchall()
    ]
    return render_template(
        "alt_scoring/indiv_sleaze.html",
        indiv_sleaze=data,
    )


@blueprint.route("/indiv_hains")
def indiv_hains():
    q = indiv_segment_query(join_miles=True)
    data = [
        (x["athlete_name"], x["segment_rides"], x["dist"])
        for x in meta.engine.execute(q, segment_id=1081507).fetchall()
    ]
    return render_template(
        "alt_scoring/indiv_hains.html",
        indiv_hains=data,
    )


@blueprint.route("/indiv_freeze")
def indiv_freeze():
    friends = request.args.get("friends", "false") == "true"
    q = indiv_freeze_query(friends)
    data = [
        (x["athlete_name"], x["freeze_points_total"])
        for x in meta.scoped_session().execute(q).fetchall()
    ]
    return render_template(
        "alt_scoring/indiv_freeze.html",
        indiv_freeze=data,
        friends=friends,
    )
