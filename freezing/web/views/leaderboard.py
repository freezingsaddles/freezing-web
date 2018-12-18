from flask import url_for, render_template, Blueprint
from sqlalchemy import text
from werkzeug.utils import redirect

from freezing.model import meta
from freezing.web import config

blueprint = Blueprint('leaderboard', __name__)


@blueprint.route("/")
def leaderboard():
    return redirect(url_for('.team_leaderboard'))


@blueprint.route("/team")
def team_leaderboard():
    return render_template('leaderboard/team.html',
                           competition_title=config.COMPETITION_TITLE)


@blueprint.route("/team_text")
def team_leaderboard_classic():
    # Get teams sorted by points
    q = text("""
             select T.id as team_id, T.name as team_name, sum(DS.points) as total_score,
             sum(DS.distance) as total_distance
             from daily_scores DS
             join teams T on T.id = DS.team_id
             where not T.leaderboard_exclude
             group by T.id, T.name
             order by total_score desc
             ;
             """)

    team_rows = meta.scoped_session().execute(q).fetchall() # @UndefinedVariable

    q = text("""
             select A.id as athlete_id, A.team_id, A.display_name as athlete_name,
             sum(DS.points) as total_score, sum(DS.distance) as total_distance,
             count(DS.points) as days_ridden
             from daily_scores DS
             join athletes A on A.id = DS.athlete_id
             group by A.id, A.display_name
             order by total_score desc
             ;
             """)

    team_members = {}
    for indiv_row in meta.scoped_session().execute(q).fetchall(): # @UndefinedVariable
        team_members.setdefault(indiv_row['team_id'], []).append(indiv_row)

    for team_id in team_members:
        team_members[team_id] = reversed(sorted(team_members[team_id], key=lambda m: m['total_score']))

    return render_template('leaderboard/team_text.html',
                           team_rows=team_rows,
                           team_members=team_members,
                           competition_title=config.COMPETITION_TITLE)


@blueprint.route("/team_various")
def team_leaderboard_various():
    return render_template('leaderboard/team_various.html',
                           competition_title=config.COMPETITION_TITLE)


@blueprint.route("/individual")
def indiv_leaderboard():
    return render_template('leaderboard/indiv.html',
                           competition_title=config.COMPETITION_TITLE)


@blueprint.route("/individual_text")
def individual_leaderboard_text():

    q = text("""
             select A.id as athlete_id, A.team_id, A.display_name as athlete_name, T.name as team_name,
             sum(DS.distance) as total_distance, sum(DS.points) as total_score,
             count(DS.points) as days_ridden
             from daily_scores DS
             join lbd_athletes A on A.id = DS.athlete_id
             join teams T on T.id = A.team_id
             where not T.leaderboard_exclude
             group by A.id, A.display_name
             order by total_score desc
             ;
             """)

    indiv_rows = meta.scoped_session().execute(q).fetchall() # @UndefinedVariable

    return render_template('leaderboard/indiv_text.html', indiv_rows=indiv_rows,
                           competition_title=config.COMPETITION_TITLE)


@blueprint.route("/individual_various")
def indiv_leaderboard_various():
    return render_template('leaderboard/indiv_various.html',
                           competition_title=config.COMPETITION_TITLE)
