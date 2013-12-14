from bafs import app, db, data
from flask import render_template
from bafs.model import Team, Athlete
from datetime import date, timedelta

def people_list_users():
	users_list = db.session.query(Athlete).order_by(Athlete.name)
	#tdy = date(2013, 2, 10) # For testing because DB is old
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
			if week_start <= r.start_date.date() <=week_end:
				weekly_dist += r.distance
				weekly_rides += 1
		users.append({"name":u.display_name,
			"id": u.id,
			"weekrides":weekly_rides,
			"weektotal":weekly_dist,
			"totaldist": total_dist,
			"totalrides": total_rides})
	return render_template('people/list.html', users=users, weekstart=week_start, weekend=week_end)
	
def people_show_person(user_id):
	our_user = db.session.query(Athlete).filter_by(id=user_id).first()
	our_team = db.session.query(Team).filter_by(id=our_user.team_id).first()
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
		if week_start <= r.start_date.date() <=week_end:
			weekly_dist += r.distance
			weekly_rides += 1		
	return render_template('people/show.html', data={
		"user":our_user, 
		"team":our_team,
		"weekrides":weekly_rides,
		"weektotal":weekly_dist,
		"totaldist": total_dist,
		"totalrides": total_rides})
