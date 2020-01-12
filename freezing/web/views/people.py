from datetime import date, timedelta
from datetime import datetime

from flask import render_template, Blueprint, abort
from sqlalchemy import text

from freezing.model import meta
from freezing.model.orm import Team, Athlete

from freezing.web import config

from pytz import utc, timezone


blueprint = Blueprint('people', __name__)


def get_local_datetime():
    # Thanks Stack Overflow https://stackoverflow.com/a/25265611/424301
    return utc.localize(
            datetime.now(),
            is_dst=None
            ).astimezone(config.TIMEZONE)


def get_today():
    """
    Sometimes you have an old database for testing and you need to set today to be something that is not actually today
    """
    if False:
        return date(2013, 2, 10)
    return get_local_datetime()


@blueprint.route("/")
def people_list_users():
    users_list = meta.scoped_session().query(Athlete).filter(Athlete.team.has(leaderboard_exclude=0)).order_by(Athlete.name)  # @UndefinedVariable
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
        users.append({"name": u.display_name,
                      "id": u.id,
                      "weekrides": weekly_rides,
                      "weektotal": weekly_dist,
                      "totaldist": total_dist,
                      "totalrides": total_rides})
    return render_template('people/list.html',
                           users=users,
                           weekstart=week_start,
                           weekend=week_end,
                           competition_title=config.COMPETITION_TITLE)


@blueprint.route("/<user_id>")
def people_show_person(user_id):
    our_user = meta.scoped_session().query(Athlete).filter_by(id=user_id).first()
    if our_user.profile_photo and not str.startswith(our_user.profile_photo, 'http'):
        our_user.profile_photo = 'https://www.strava.com/' + our_user.profile_photo
    if not our_user:
        abort(404)

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
    return render_template('people/show.html', data={
        "user": our_user,
        "team": our_team,
        "weekrides": weekly_rides,
        "weektotal": weekly_dist,
        "totaldist": total_dist,
        "totalrides": total_rides},
        competition_title=config.COMPETITION_TITLE)


@blueprint.route("/ridedays")
def ridedays():
    q = text("""
                SELECT
                    a.id,
                    a.display_name,
                    count(b.ride_date) as rides,
                    sum(b.distance) as miles,
                    max(b.ride_date) as lastride
                FROM
                    lbd_athletes a,
                    daily_scores b where a.id = b.athlete_id
                group by b.athlete_id
                order by
                    rides desc,
                    miles desc,
                    display_name
                ;
                """)
    loc_time = get_today()
    loc_total_days = loc_time.timetuple().tm_yday
    ride_days = [(
        x['id'],
        x['display_name'],
        x['rides'],
        x['miles'],
        x['lastride'] >= loc_time.date())
        for x in meta.scoped_session().execute(q).fetchall()]
    return render_template(
            'people/ridedays.html',
            ride_days=ride_days,
            num_days=loc_total_days)


@blueprint.route("/friends")
def friends():
    q = text("""
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
             """)

    indiv_rows = meta.scoped_session().execute(q).fetchall() # @UndefinedVariable

    return render_template('people/friends.html', indiv_rows=indiv_rows,
                           competition_title=config.COMPETITION_TITLE)
