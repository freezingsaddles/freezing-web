from datetime import datetime, timedelta
from math import ceil

from flask import Blueprint, abort, render_template
from freezing.model import meta
from freezing.model.orm import Athlete, Team
from pytz import timezone, utc
from sqlalchemy import text

from freezing.web import config
from freezing.web.utils.tribes import load_tribes, query_tribes

blueprint = Blueprint("people", __name__)


def get_local_datetime() -> datetime:
    # Thanks Stack Overflow https://stackoverflow.com/a/25265611/424301
    return utc.localize(datetime.now(), is_dst=None).astimezone(config.TIMEZONE)


def get_today() -> datetime:
    """
    Sometimes you have an old database for testing and you need to set today to be something that is not actually today
    """
    if False:
        return datetime(2024, 3, 18, tzinfo=config.TIMEZONE)
    return get_local_datetime()


@blueprint.route("/")
def people_list_users():
    users_list = (
        meta.scoped_session()
        .query(Athlete)
        .filter(Athlete.team.has(leaderboard_exclude=0))
        .order_by(Athlete.display_name)
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
        our_user.profile_photo = None

    our_team = meta.scoped_session().query(Team).filter_by(id=our_user.team_id).first()
    today = get_today()
    week_start = today.date() - timedelta(days=(today.weekday()) % 7)
    week_end = week_start + timedelta(days=6)
    today_dist = 0
    today_rides = 0
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
        if ride_date == today.date():
            today_dist += r.distance
            today_rides += 1

    q = text(
        """
           with daily_rides as (
            select date(CONVERT_TZ(R.start_date, R.timezone, :timezone)) as ride_date,
            R.distance as distance,
            W.ride_temp_avg as ride_temp
            from rides R left outer join ride_weather W on W.ride_id = R.id
            where R.athlete_id = :athlete_id
          )
          select ride_date, sum(distance) as distance, avg(ride_temp) as ride_temp
            from daily_rides
            group by ride_date
            order by ride_date;
            """
    ).bindparams(athlete_id=user_id, timezone=config.TIMEZONE)

    indiv_q = meta.scoped_session().execute(q).fetchall()
    start = config.START_DATE - timedelta(days=(config.START_DATE.weekday() + 1) % 7)
    weeks = ceil((config.END_DATE - start).days / 7)

    def color(res) -> str:
        distance = res._mapping["distance"]
        temp = res._mapping["ride_temp"]
        hue = int(min(360, max(240, 300 + (temp - 44) * 6))) if temp else 300
        sat = 100  # max(1, min(100, int(distance * 10)))
        lig = int(50 + min(25, max(0, (distance - 10))))
        alp = int(min(100, max(0, distance * 5)))
        return f"hsla({hue}, {sat}%, {lig}%, {alp}%)"

    mosaic = {
        (res._mapping["ride_date"] - start.date()).days: color(res) for res in indiv_q
    }

    tribal_groups = load_tribes()
    my_tribes = query_tribes(user_id)

    return render_template(
        "people/show.html",
        data={
            "environment": config.ENVIRONMENT,
            "my_tribes": my_tribes,
            "team": our_team,
            "todaydist": today_dist,
            "todayrides": today_rides,
            "totaldist": total_dist,
            "totalrides": total_rides,
            "tribal_groups": tribal_groups,
            "user": our_user,
            "weekrides": weekly_rides,
            "weektotal": weekly_dist,
            "mosaic": mosaic,
            "weeks": weeks,
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
                    sum(case when b.ride_date = :today then 1 else 0 end) as today
                FROM
                    lbd_athletes a,
                    daily_scores b where a.id = b.athlete_id
                group by b.athlete_id
                order by
                    case when rides = :total then 0 when rides = :total - 1 and today = 0 then 1 else 2 end,
                    rides desc,
                    display_name
                ;
                """
    )
    loc_time = get_today()
    loc_total_days = (
        min(loc_time.toordinal(), config.END_DATE.toordinal())
        - config.START_DATE.toordinal()
        + 1
    )
    all_done = competition_done(loc_time)

    def contender(rides: int, today: int) -> bool:
        return rides == loc_total_days - 1 and today == 0 and not all_done

    ride_days = [
        (
            x._mapping["id"],
            x._mapping["display_name"],
            x._mapping["rides"],
            x._mapping["miles"],
            contender(x._mapping["rides"], x._mapping["today"]),
        )
        for x in meta.scoped_session()
        .execute(q.bindparams(today=loc_time.date(), total=loc_total_days))
        .fetchall()
    ]
    return render_template(
        "people/ridedays.html",
        ride_days=ride_days,
        num_days=loc_total_days,
        all_done=all_done,
        every_day_riders=sum(x[2] == loc_total_days for x in ride_days),
        contenders=sum(x[4] for x in ride_days),
        remainders=sum(x[2] < loc_total_days and not x[4] for x in ride_days),
    )


@blueprint.route("/friends")
def friends():
    q = text(
        """
             select A.id, A.team_id, A.display_name as athlete_name, T.name as team_name,
             sum(DS.distance) as total_distance, sum(DS.points) as total_score,
             count(DS.points) as days_ridden
             from daily_scores DS
             join athletes A on A.id = DS.athlete_id
             join teams T on T.id = A.team_id
             where T.leaderboard_exclude
             group by A.id, A.display_name
             order by lower(A.display_name) asc
             ;
             """
    )

    indiv_rows = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    return render_template(
        "people/friends.html",
        indiv_rows=indiv_rows,
    )
