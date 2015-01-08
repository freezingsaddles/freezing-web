from datetime import date, timedelta
from datetime import datetime

from flask import render_template, Blueprint
from sqlalchemy import text

from bafs import db
from bafs.model import Team, Athlete


blueprint = Blueprint('people', __name__)


@blueprint.route("/")
def people_list_users():
    users_list = db.session.query(Athlete).order_by(Athlete.name)  # @UndefinedVariable
    # tdy = date(2013, 2, 10) # For testing because DB is old
    tdy = date.today()
    week_start = tdy - timedelta(days=(tdy.weekday() + 1) % 7)
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
            if week_start <= r.start_date.date() <= week_end:
                weekly_dist += r.distance
                weekly_rides += 1
        users.append({"name": u.display_name,
                      "id": u.id,
                      "weekrides": weekly_rides,
                      "weektotal": weekly_dist,
                      "totaldist": total_dist,
                      "totalrides": total_rides})
    return render_template('people/list.html', users=users, weekstart=week_start, weekend=week_end)


@blueprint.route("/<user_id>")
def people_show_person(user_id):
    our_user = db.session.query(Athlete).filter_by(id=user_id).first()  # @UndefinedVariable
    our_team = db.session.query(Team).filter_by(id=our_user.team_id).first()  # @UndefinedVariable
    tdy = date.today()
    week_start = tdy - timedelta(days=(tdy.weekday() + 1) % 7)
    week_end = week_start + timedelta(days=6)
    weekly_dist = 0
    weekly_rides = 0
    total_rides = 0
    total_dist = 0
    for r in our_user.rides:
        total_rides += 1
        total_dist += r.distance
        if week_start <= r.start_date.date() <= week_end:
            weekly_dist += r.distance
            weekly_rides += 1
    return render_template('people/show.html', data={
        "user": our_user,
        "team": our_team,
        "weekrides": weekly_rides,
        "weektotal": weekly_dist,
        "totaldist": total_dist,
        "totalrides": total_rides})


@blueprint.route("/ridedays")
def ridedays():
    q = text("""
		SELECT a.id, a.display_name, count(b.ride_date) as rides, sum(b.distance) as miles, max(b.ride_date) as lastride
		 FROM athletes a, daily_scores b where a.id = b.athlete_id group by b.athlete_id order by rides desc, miles desc, display_name
		;
		"""
    )
    total_days = datetime.now().timetuple().tm_yday
    ride_days = [(x['id'], x['display_name'], x['rides'], x['miles'], x['lastride'] >= date.today()) for x in
                 db.session.execute(q).fetchall()]
    return render_template('people/ridedays.html', ride_days=ride_days, num_days=total_days)
