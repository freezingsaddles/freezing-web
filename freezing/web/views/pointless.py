import os
import operator
from datetime import date, datetime, timezone
from collections import defaultdict
import re

from flask import render_template, Blueprint, abort, redirect, url_for
from sqlalchemy import text
import yaml

from freezing.model import meta
from freezing.web.config import config
from freezing.web.exc import ObjectNotFound
from freezing.web.utils.genericboard import load_board_and_data

blueprint = Blueprint('pointless', __name__)


@blueprint.route('/generic/<leaderboard>')
def generic(leaderboard):
    try:
        board, data = load_board_and_data(leaderboard)
    except ObjectNotFound:
        abort(404)
    else:
        return render_template('pointless/generic.html', fields=board.fields, title=board.title,
                               description=board.description, url=board.url, data=data)


@blueprint.route("/avgspeed")
def averagespeed():
    return generic('avgspeed')


@blueprint.route("/avgdist")
def shortride():
    return generic('avgdist')


@blueprint.route("/dirtybiker")
def dirtybiker():
    return generic("dirtybiker")


@blueprint.route("/billygoat-team")
def billygoat_team():
    return generic('billygoat-team')


@blueprint.route("/billygoat-indiv")
def billygoat_invid():
    return generic('billygoat-indiv')


@blueprint.route("/tortoiseteam")
def tortoiseteam():
    return generic('tortoiseteam')


@blueprint.route("/weekend")
def weekendwarrior():
    return generic('weekend')


@blueprint.route("/avgtemp")
def avgtemp():
    """ sum of ride distance * ride avg temp divided by total distance """
    return generic('/avgtemp')


@blueprint.route("/kidmiles")
def kidmiles():
    return generic('kidmiles')


@blueprint.route("/opmdays")
def opmdays():
    """
    If OPM doesn't close this year, just use Michigan's birthday for Kitty's prize
    """
    return generic('opmdays')

@blueprint.route("/points_per_mile")
def points_per_mile():
    """
    Note: set num_days to the minimum number of ride days to be eligible for the prize.
    This was 33 in 2017, 36 in 2018, and 40 in 2019.

    (@hozn noted: I didn't pay enough attention to determine if this is something we can calculate.)
    """
    num_days = 40
    query = text("""
        select
            A.id,
            A.display_name as athlete_name,
            sum(B.distance) as dist,
            sum(B.points) as pnts,
            count(B.athlete_id) as ridedays
        from lbd_athletes A join daily_scores B on A.id = B.athlete_id group by athlete_id;
    """)
    ppm = [(x['athlete_name'], x['pnts'], x['dist'], (x['pnts']/x['dist']), x['ridedays'])
           for x in meta.scoped_session().execute(query).fetchall()]
    ppm.sort(key=lambda tup: tup[3], reverse=True)
    return render_template('pointless/points_per_mile.html', data={"riders":ppm, "days":num_days})

def _get_hashtag_tdata(hashtag, orderby=1):
    """
    if orderby = 1 then order by mileage. Else by #rides
    """
    sess = meta.scoped_session()
    if orderby == 1:
        sortkeyidx = (3, 2)
    else:
        sortkeyidx = (2, 3)
    q = text ("""
        select A.id, A.display_name as athlete_name, count(R.id) as hashtag_rides,
        sum(R.distance) as hashtag_miles
        from athletes A
        join rides R on R.athlete_id = A.id
        where R.name like concat('%', '#', :hashtag, '%')
        group by A.id, A.display_name;
        """)
    rs = sess.execute(q, params=dict(hashtag=hashtag))
    retval = [(x['id'], x['athlete_name'], x['hashtag_rides'], x['hashtag_miles']) for x in rs.fetchall()]
    return sorted(retval, key = operator.itemgetter(*sortkeyidx), reverse=True)

@blueprint.route("/hashtag/<string:hashtag>")
def hashtag_leaderboard(hashtag):
    ht = ''.join(ch for ch in hashtag if ch.isalnum())
    tdata = _get_hashtag_tdata(ht)
    return render_template('pointless/hashtag.html', data={"tdata":tdata, "hashtag":"#" + ht, "hashtag_notag":ht})

@blueprint.route("/coffeeride")
def coffeeride():
    year = datetime.now().year
    tdata = _get_hashtag_tdata("FS{0}coffeeride".format(year), 2)
    return render_template('pointless/coffeeride.html', data={"tdata":tdata, 'year':year})

@blueprint.route("/pointlesskids")
def pointlesskids():
    q = text("""
        select name, distance from rides where upper(name) like '%WITHKID%';
    """)
    rs = meta.scoped_session().execute(q)
    d = defaultdict(int)
    for x in rs.fetchall():
        for match in re.findall('(#withkid\w+)', x['name']):
            d[match.replace('#withkid', '')] += x['distance']
    return render_template('pointless/pointlesskids.html', data={'tdata':sorted(d.items(), key=lambda v: v[1], reverse=True)})


@blueprint.route("/tandem")
def tandem():
    """
    Really this should not have been defined as a specific endpoint, since it is
    available as a generic. Redirect to the generic leaderboard instead.
    """
    return redirect("/pointless/generic/tandem")

@blueprint.route("/kidsathlon")
def kidsathlon():
    q = text("""
        select
        A.id as athlete_id,
        A.display_name as athlete_name,
        sum(case when (upper(R.name) like '%#KIDICAL%' and upper(R.name) like '%#WITHKID%') then R.distance else 0 end) as miles_both,
        sum(case when (upper(R.name) like '%#KIDICAL%' and upper(R.name) not like '%#WITHKID%')then R.distance else 0 end) as kidical,
        sum(case when (upper(R.name) like '%#WITHKID%' and upper(R.name) not like '%#KIDICAL%') then R.distance else 0 end) as withkid
        from lbd_athletes A
        join rides R on R.athlete_id = A.id
        where (upper(R.name) like '%#KIDICAL%' or upper(R.name) like '%#WITHKID%')
        group by A.id, A.display_name
    """)
    data = []
    for x in meta.scoped_session().execute(q).fetchall():
        miles_both = float(x['miles_both'])
        kidical = miles_both + float(x['kidical'])
        withkid = miles_both + float(x['withkid'])
        if kidical > 0 and withkid > 0:
            kidsathlon = kidical + withkid - miles_both
        else:
            kidsathlon = float(0)
        data.append((x['athlete_id'], x['athlete_name'], kidical, withkid, kidsathlon))
    return render_template('pointless/kidsathlon.html', data={'tdata':sorted(data, key=lambda v: v[4], reverse=True)})

@blueprint.route("/daily_variance")
def daily_variance():
    q = text("""
        select a.display_name as name, vbd.* from variance_by_day vbd, lbd_athletes a where vbd.athlete_id=a.id
    """)
    days_left = (config.END_DATE - datetime.now(timezone.utc)).days #how many days left in the competition
    if days_left < 0:
        days_left = 0
    min_days = 50 # minimum number of ride days to qualify, Chris inititally said 2/3 and this is a nice round number close to 2/3
    data = []
    for x in meta.scoped_session().execute(q).fetchall():
        days_raw = [x['mon_var_pop'], x['tue_var_pop'], x['wed_var_pop'], x['thu_var_pop'], x['fri_var_pop'], x['sat_var_pop'], x['sun_var_pop']]
        days = [x for x in days_raw if x is not None]
        avg = round(sum(days)/len(days), 2)
        qualified = x['ride_days'] + days_left >= min_days #Either you've ridden enough days or you still can ride enough days
        if qualified:
            qualified = float(x['total_miles'])/float(x['ride_days']) > float(2.00) #you're averaging more than 2 miles per day you ride
        days_clean = [round(x, 2) if x is not None else '-' for x in days_raw]
        data.append((x['athlete_id'], x['name'], x['ride_days'], round(x['total_miles'],1), qualified , avg,) + tuple(days_clean))
    return render_template("pointless/daily_variance.html", data={'tdata':data, 'min_days':min_days})
