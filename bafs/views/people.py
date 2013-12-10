from bafs import app, db, data
from flask import render_template
from bafs.model import Team, Athlete

def people_list_users():
	users_list = db.session.query(Athlete).order_by(Athlete.name)
	return render_template('people/list.html', users=users_list)
	
def people_show_person(user_id):
	our_user = db.session.query(Athlete).filter_by(id=user_id).first()
	our_team = db.session.query(Team).filter_by(id=our_user.team_id).first()
	return render_template('people/show.html', user=our_user, team=our_team)
