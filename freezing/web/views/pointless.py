import os
import operator
from datetime import date, datetime
from collections import defaultdict
import re

from flask import render_template, Blueprint, abort
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
    Note: set num_days to the minimum number of ride days to be eligible for the prize. This was 33 in 2017, 36 in 2019.
    I didn't pay enough attention to determine if this is something we can calculate.
    """
    num_days = 36
    q = text("""
        select A.id, A.display_name as athlete_name, sum(B.distance) as dist, sum(B.points) as pnts, count(B.athlete_id) as ridedays
        from lbd_athletes A join daily_scores B on A.id = B.athlete_id group by athlete_id;
    """)
    ppm = [(x['athlete_name'], x['pnts'], x['dist'],(x['pnts']/x['dist']), x['ridedays']) for x in meta.scoped_session().execute(q).fetchall()]
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
