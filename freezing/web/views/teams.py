from flask import Blueprint, abort, render_template
from freezing.model import meta
from freezing.model.orm import Team
from sqlalchemy import text

blueprint = Blueprint("teams", __name__)


@blueprint.route("/<team_id>")
def teams_show_team(team_id):
    our_team = meta.scoped_session().query(Team).filter_by(id=team_id).first()
    if not our_team:
        abort(404)

    if our_team.profile_photo and not str.startswith(our_team.profile_photo, "http"):
        our_team.profile_photo = None

    q = text(
        """
             select
               A.id as athlete_id,
               A.display_name as athlete_name,
               sum(DS.distance) as total_distance,
               sum(DS.points) as total_score,
               count(DS.points) as days_ridden
             from
               daily_scores DS
                 join lbd_athletes A on A.id = DS.athlete_id
             where A.team_id = :team
             group by A.id, A.display_name
             order by display_name asc
             ;
             """
    ).params(team=team_id)

    members = meta.scoped_session().execute(q).fetchall()

    return render_template(
        "teams/show.html",
        team=our_team,
        members=[m for m in members],
    )
