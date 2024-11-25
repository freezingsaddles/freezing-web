from flask import Blueprint, render_template, url_for
from freezing.model import meta
from sqlalchemy import text
from werkzeug.utils import redirect

from freezing.web.views.shared_sql import team_leaderboard_query

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

    for team_id in team_members:
        team_members[team_id] = reversed(
            sorted(team_members[team_id], key=lambda m: m["total_score"])
        )

    return render_template(
        "leaderboard/team_text.html",
        team_rows=team_rows,
        team_members=team_members,
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
    )


@blueprint.route("/individual_various")
def indiv_leaderboard_various():
    return render_template(
        "leaderboard/indiv_various.html",
    )
