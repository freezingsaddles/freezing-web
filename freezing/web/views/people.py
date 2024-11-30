from datetime import datetime, timedelta

from flask import Blueprint, abort, render_template
from pytz import timezone, utc
from sqlalchemy import text

from freezing.model import meta
from freezing.model.orm import Athlete, Team
from freezing.web import config

blueprint = Blueprint("people", __name__)


def get_local_datetime() -> datetime:
    # Thanks Stack Overflow https://stackoverflow.com/a/25265611/424301
    return utc.localize(datetime.now(), is_dst=None).astimezone(config.TIMEZONE)


def get_today() -> datetime:
    """
    Sometimes you have an old database for testing and you need to set today to be something that is not actually today
    """
    if False:
        return datetime(2019, 3, 20, tzinfo=config.TIMEZONE)
    return get_local_datetime()


@blueprint.route("/")
def people_list_users():
    users_list = (
        meta.scoped_session()
        .query(Athlete)
        .filter(Athlete.team.has(leaderboard_exclude=0))
        .order_by(Athlete.name)
    )  # @UndefinedVariable
    today = get_today()
    week_start = today.date() - timedelta(days=(today.weekday()) % 7)
    week_end = week_start + timedelta(days=6)
    users = []
    for u in users_list:
        weekly_dist = 0
        weekly_rides = 0
        total_rides = 0
        total_dist = 0
        for r in u.rides:
            total_rides += 1
            total_dist += r.distance
            ride_date = r.start_date.replace(tzinfo=timezone(r.timezone)).date()
            if week_start <= ride_date <= week_end:
                weekly_dist += r.distance
                weekly_rides += 1
        users.append(
            {
                "name": u.display_name,
                "id": u.id,
                "weekrides": weekly_rides,
                "weektotal": weekly_dist,
                "totaldist": total_dist,
                "totalrides": total_rides,
            }
        )
    return render_template(
        "people/list.html",
        users=users,
        weekstart=week_start,
        weekend=week_end,
    )


@blueprint.route("/<user_id>")
def people_show_person(user_id):
    our_user = meta.scoped_session().query(Athlete).filter_by(id=user_id).first()
    if not our_user:
        abort(404)
    if our_user.profile_photo and not str.startswith(our_user.profile_photo, "http"):
        our_user.profile_photo = "https://www.strava.com/" + our_user.profile_photo

    our_team = meta.scoped_session().query(Team).filter_by(id=our_user.team_id).first()
    today = get_today()
    week_start = today.date() - timedelta(days=(today.weekday()) % 7)
    week_end = week_start + timedelta(days=6)
    weekly_dist = 0
    weekly_rides = 0
    total_rides = 0
    total_dist = 0
    for r in our_user.rides:
        total_rides += 1
        total_dist += r.distance
        ride_date = r.start_date.replace(tzinfo=timezone(r.timezone)).date()
        if week_start <= ride_date <= week_end:
            weekly_dist += r.distance
            weekly_rides += 1
    return render_template(
        "people/show.html",
        data={
            "user": our_user,
            "team": our_team,
            "weekrides": weekly_rides,
            "weektotal": weekly_dist,
            "totaldist": total_dist,
            "totalrides": total_rides,
        },
    )


def competition_done(loc_time):
    end_time = config.END_DATE
    return loc_time > end_time


@blueprint.route("/ridedays")
def ridedays():
    q = text(
        """
                SELECT
                    a.id,
                    a.display_name,
                    count(b.ride_date) as rides,
                    sum(b.distance) as miles,
                    max(b.ride_date) < :today as contender
                FROM
                    lbd_athletes a,
                    daily_scores b where a.id = b.athlete_id
                group by b.athlete_id
                order by
                    rides desc,
                    contender desc,
                    miles desc,
                    display_name
                ;
                """
    )
    loc_time = get_today()
    start_yday = config.START_DATE.timetuple().tm_yday
    end_yday = config.END_DATE.timetuple().tm_yday
    current_yday = loc_time.timetuple().tm_yday
    loc_total_days = min(current_yday, end_yday) - start_yday + 1
    all_done = competition_done(loc_time)
    # once the competition is over, even if you're a day short you are no longer a contender
    contender_date = config.END_DATE.date() if all_done else loc_time.date()
    ride_days = [
        (
            x["id"],
            x["display_name"],
            x["rides"],
            x["miles"],
        )
        for x in meta.engine.execute(q, today=contender_date).fetchall()
    ]
    return render_template(
        "people/ridedays.html",
        ride_days=ride_days,
        num_days=loc_total_days,
        all_done=all_done,
    )


@blueprint.route("/friends")
def friends():
    q = text(
        """
             select A.id as athlete_id, A.team_id, A.display_name as athlete_name, T.name as team_name,
             sum(DS.distance) as total_distance, sum(DS.points) as total_score,
             count(DS.points) as days_ridden
             from daily_scores DS
             join athletes A on A.id = DS.athlete_id
             join teams T on T.id = A.team_id
             where T.leaderboard_exclude
             group by A.id, A.display_name
             order by total_score desc
             ;
             """
    )

    indiv_rows = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    return render_template(
        "people/friends.html",
        indiv_rows=indiv_rows,
    )
