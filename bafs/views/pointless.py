from flask import render_template
from flask import render_template, Blueprint
from sqlalchemy import text

from bafs import app, db, data

blueprint = Blueprint('pointless', __name__)


@blueprint.route("/avgspeed")
def averagespeed():
    q = text("""
        select a.id, a.display_name, avg(b.average_speed) as speed from athletes a, rides b where a.id = b.athlete_id group by a.id order by speed;
        """)
    avgspeed = [(x['id'], x['display_name'], x['speed']) for x in db.session.execute(q).fetchall()]
    return render_template('pointless/averagespeed.html', avg=avgspeed)


@blueprint.route("/avgdist")
def shortride():
    q = text("""
        select a.id, a.display_name, avg(b.distance) as dist, count(distinct(date(b.start_date))) as distrides from athletes a,
        rides b where a.id = b.athlete_id group by a.id order by dist;
        """)
    avgdist = [(x['id'], x['display_name'], x['dist']) for x in db.session.execute(q).fetchall() if
               x['distrides'] >= 10]
    return render_template('pointless/distance.html', avg=avgdist)


@blueprint.route("/billygoat")
def billygoat():
    q = text("""
    select sum(a.elevation_gain) as elev,sum(a.distance) as dist, (sum(a.elevation_gain)/sum(a.distance)) as gainpermile,
    c.name from rides a, athletes b, teams c where a.athlete_id=b.id and b.team_id=c.id group by c.name order by gainpermile desc;
    """)
    goat = [(x['name'], x['gainpermile'], x['dist'], x['elev']) for x in db.session.execute(q).fetchall()]
    return render_template('pointless/billygoat.html', data=goat)


@blueprint.route("/tortoiseteam")
def tortoiseteam():
    q = text("""
    select avg(a.average_speed) as spd,    c.name from rides a, athletes b, teams c where a.athlete_id=b.id and b.team_id=c.id group by c.name order by spd asc;
    """)
    goat = [(x['name'], x['spd']) for x in db.session.execute(q).fetchall()]
    return render_template('pointless/tortoiseteam.html', data=goat)


@blueprint.route("/weekend")
def weekendwarrior():
    q = text("""
        select A.id as athlete_id, A.display_name as athlete_name, sum(DS.points) as total_score,
        sum(if((dayofweek(DS.ride_date)=7 or (dayofweek(DS.ride_date)=1)) , DS.points, 0)) as 'weekend',
        sum(if((dayofweek(DS.ride_date)<7 and (dayofweek(DS.ride_date)>1)) , DS.points, 0)) as 'weekday'
        from daily_scores DS join athletes A on A.id = DS.athlete_id group by A.id
        order by weekend desc;
        """)
    weekend = [(x['athlete_id'], x['athlete_name'], x['total_score'], x['weekend'], x['weekday']) for x in
               db.session.execute(q).fetchall()]
    return render_template('people/weekend.html', data=weekend)

@blueprint.route("/avgtemp")
def avgtemp():
    """ sum of ride distance * ride avg temp divided by total distance """
    q = text("""
        select athlete_id, athlete_name, sum(temp_dist)/sum(distance) as avgtemp from (
        select A.id as athlete_id, A.display_name as athlete_name, W.ride_temp_avg, R.distance,
        W.ride_temp_avg * R.distance as temp_dist
        from athletes A, ride_weather W, rides R where R.athlete_id = A.id and R.id=W.ride_id) as T
        group by athlete_id, athlete_name order by avgtemp asc;
        """)
    tdata = [(x['athlete_id'], x['athlete_name'], x['avgtemp']) for x in db.session.execute(q).fetchall()]
    return render_template('pointless/averagetemp.html', data=tdata)

@blueprint.route("/kidmiles")
def kidmiles():
    q = text ("""
        select A.id, A.display_name as athlete_name, count(R.id) as kidical_rides,
        sum(R.distance) as kidical_miles
        from athletes A
        join rides R on R.athlete_id = A.id
        where R.name like '%#kidical%'
        group by A.id, A.display_name
        order by kidical_miles desc, kidical_rides desc;
        """)
    tdata = [(x['id'], x['athlete_name'], x['kidical_rides'], x['kidical_miles']) for x in db.session.execute(q).fetchall()]
    return render_template('pointless/kidmiles.html', data=tdata)

@blueprint.route("/opmdays")
def opmdays():
    q = text("""
        select A.id, A.display_name as athlete_name, count(distinct(date(R.start_date))) as days, sum(R.distance) as distance
        from athletes A join rides R on R.athlete_id=A.id
        where date(R.start_date) in ('2016-01-15', '2016-01-11') group by R.athlete_id
        order by days desc, distance desc;
        """)
    opm = [(x['id'], x['athlete_name'], x['days'], x['distance']) for x in
               db.session.execute(q).fetchall()]
    return render_template('pointless/opmdays.html', data=opm)
