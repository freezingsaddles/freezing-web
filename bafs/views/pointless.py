from bafs import app, db, data
from flask import render_template
from sqlalchemy import text

def averagespeed():
	q = text("""
		select a.id, a.display_name, avg(b.average_speed) as speed from athletes a, rides b where a.id = b.athlete_id group by a.id order by speed;
		""")
	avgspeed = [(x['id'], x['display_name'], x['speed']) for x in db.session.execute(q).fetchall()]	
	return render_template('people/averagespeed.html', avg = avgspeed)

def shortride():
	q = text("""
		select a.id, a.display_name, avg(b.distance) as dist, count(distinct(date(b.start_date))) as distrides from athletes a, 
		rides b where a.id = b.athlete_id group by a.id order by dist;
		""")
	avgdist = [(x['id'], x['display_name'], x['dist']) for x in db.session.execute(q).fetchall() if x['distrides']>=10]	
	return render_template('people/distance.html', avg = avgdist) 
