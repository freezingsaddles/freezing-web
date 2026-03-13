from datetime import timedelta
from math import ceil

from flask import Blueprint, abort, render_template
from freezing.model import meta
from freezing.model.orm import Team
from sqlalchemy import text

from freezing.web import config

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

    q = text(
        """
           with daily_rides as (
            select date(CONVERT_TZ(R.start_date, R.timezone, :timezone)) as ride_date,
            A.id as athlete_id,
            sum(R.distance) as distance
            from rides R inner join athletes A on A.id = R.athlete_id
            where A.team_id = :team_id
            group by ride_date, athlete_id
          )
          select ride_date, count(athlete_id) as athletes
            from daily_rides
            where distance >= 1
            group by ride_date
            order by ride_date;
            """
    ).bindparams(team_id=team_id, timezone=config.TIMEZONE)

    indiv_q = meta.scoped_session().execute(q).fetchall()
    start = config.START_DATE - timedelta(days=(config.START_DATE.weekday() + 1) % 7)
    weeks = ceil((config.END_DATE - start).days / 7)

    count = len(members)

    def color(res) -> str:
        athletes = res._mapping["athletes"]
        alp = int(min(100, max(0, athletes * 100 // count))) if count else 0
        lig = 45 if athletes < (count - 2) else 50 + 15 * (athletes - count + 2)
        return f"hsla(197, 97%, {lig}%, {alp}%)"

    mosaic = {
        (res._mapping["ride_date"] - start.date()).days: color(res) for res in indiv_q
    }

    return render_template(
        "teams/show.html",
        team=our_team,
        members=[m for m in members],
        mosaic=mosaic,
        weeks=weeks,
        first_day=(config.START_DATE - start).days,
        last_day=(config.END_DATE - start).days,
    )
