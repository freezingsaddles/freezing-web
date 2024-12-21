import operator
import re
from collections import defaultdict
from datetime import datetime, timezone

from flask import Blueprint, abort, render_template
from freezing.model import meta
from sqlalchemy import text

from freezing.web.config import config
from freezing.web.exc import ObjectNotFound
from freezing.web.utils.genericboard import format_rows, load_board, load_board_and_data
from freezing.web.utils.hashboard import load_hashtag

blueprint = Blueprint("pointless", __name__)


@blueprint.route("/generic/<leaderboard>")
def generic(leaderboard):
    try:
        board, data = load_board_and_data(leaderboard)
    except ObjectNotFound:
        abort(404)
    else:
        return render_template(
            "pointless/generic.html",
            fields=board.fields,
            title=board.title,
            description=board.description,
            sponsor=board.sponsor,
            url=board.url,
            data=data,
        )


@blueprint.route("/avgspeed")
def averagespeed():
    return generic("avgspeed")


@blueprint.route("/avgdist")
def shortride():
    return generic("avgdist")


@blueprint.route("/dirtybiker")
def dirtybiker():
    return generic("dirtybiker")


@blueprint.route("/billygoat-team")
def billygoat_team():
    return generic("billygoat-team")


@blueprint.route("/billygoat-indiv")
def billygoat_invid():
    return generic("billygoat-indiv")


@blueprint.route("/tortoiseteam")
def tortoiseteam():
    return generic("tortoiseteam")


@blueprint.route("/weekend")
def weekendwarrior():
    return generic("weekend")


@blueprint.route("/avgtemp")
def avgtemp():
    """sum of ride distance * ride avg temp divided by total distance"""
    return generic("/avgtemp")


@blueprint.route("/kidmiles")
def kidmiles():
    return generic("kidmiles")


@blueprint.route("/opmdays")
def opmdays():
    """
    If OPM doesn't close this year, just use Michigan's birthday for Kitty's prize
    """
    return generic("opmdays")


@blueprint.route("/points_per_mile")
def points_per_mile():
    """
    Note: set num_days to the minimum number of ride days to be eligible for the prize.
    This was 33 in 2017, 36 in 2018, and 40 in 2019.

    (@hozn noted: I didn't pay enough attention to determine if this is something we can calculate.)
    """
    num_days = 40
    query = text(
        """
        select
            A.id,
            A.display_name as athlete_name,
            sum(B.distance) as dist,
            sum(B.points) as pnts,
            count(B.athlete_id) as ridedays
        from lbd_athletes A join daily_scores B on A.id = B.athlete_id group by athlete_id;
    """
    )
    ppm = [
        (
            x["athlete_name"],
            x["pnts"],
            x["dist"],
            (x["pnts"] / x["dist"]) if x["dist"] > 0 else 0,
            x["ridedays"],
        )
        for x in meta.scoped_session().execute(query).fetchall()
    ]
    ppm.sort(key=lambda tup: tup[3], reverse=True)
    return render_template(
        "pointless/points_per_mile.html", data={"riders": ppm, "days": num_days}
    )


def _get_hashtag_tdata(hashtag, alttag, orderby=1):
    """
    if orderby = 1 then order by mileage. Else by #rides
    """
    sess = meta.scoped_session()
    if orderby == 1:
        sortkeyidx = (3, 2)
    else:
        sortkeyidx = (2, 3)
    q = text(
        """
        select
            A.id,
            A.display_name as athlete_name,
            count(R.id) as hashtag_rides,
            sum(R.distance) as hashtag_miles
        from
            athletes A join
            rides R on R.athlete_id = A.id
        where
            R.name like concat('%', '#', :hashtag, '%') or
            R.name like concat('%', '#', :alttag, '%')
        group by
            A.id, A.display_name;
        """
    )
    rs = sess.execute(q, params=dict(hashtag=hashtag, alttag=alttag or hashtag))
    retval = [
        (x["id"], x["athlete_name"], x["hashtag_rides"], x["hashtag_miles"])
        for x in rs.fetchall()
    ]
    return sorted(retval, key=operator.itemgetter(*sortkeyidx), reverse=True)


@blueprint.route("/hashtag/<string:hashtag>")
def hashtag_leaderboard(hashtag):
    meta = load_hashtag(hashtag)
    ht = meta.tag if meta else "".join(ch for ch in hashtag if ch.isalnum())
    tdata = _get_hashtag_tdata(
        hashtag=ht,
        alttag=meta.alt if meta else None,
        orderby=1 if meta is None or not meta.rank_by_rides else 2,
    )
    return render_template(
        "pointless/hashtag.html",
        data={"tdata": tdata, "hashtag": "#" + ht, "hashtag_notag": ht},
        meta=meta,
    )


def _get_segment_tdata(segment):
    sess = meta.scoped_session()
    q = text(
        """
        select
            A.id,
            A.display_name      as athlete_name,
            E.segment_name      as segment_name,
            count(E.id)         as segment_rides,
            sum(E.elapsed_time) as total_time
        from
            athletes A join
            rides R on R.athlete_id = A.id join
            ride_efforts E on E.ride_id = R.id
        where
            E.segment_id = :segment
        group by
            A.id, A.display_name, E.segment_name;
        """
    )
    rs = sess.execute(q, params=dict(segment=segment))
    retval = [
        (
            x["id"],
            x["athlete_name"],
            x["segment_name"],
            x["segment_rides"],
            x["total_time"],
        )
        for x in rs.fetchall()
    ]
    return sorted(retval, key=operator.itemgetter(3), reverse=True)


@blueprint.route("/segment/<int:segment>")
def segment_leaderboard(segment):
    tdata = _get_segment_tdata(
        segment=segment,
    )
    return render_template(
        "pointless/segment.html",
        data={
            "tdata": tdata,
            "segment_id": segment,
            "segment_name": tdata[0][2] if tdata else "Unknown Segment",
        },
        meta=meta,
    )


def _get_ross_hill_loop_tdata():
    sess = meta.scoped_session()
    # counts whichever loop you have done more efforts on for a given ride, because the loops
    # overlap so two loops on 1072528 means one on 4934241 and vice versa.
    q = text(
        """
         select
            Q.id,
            Q.display_name as athlete_name,
            sum(greatest(righteous, wrongeous)) as segment_rides,
            sum(case when righteous > wrongeous THEN righttime ELSE wrongtime end) AS total_time
         from (
            select
              A.id,
              A.display_name,
              R.id as ride_id,
              sum(case when E.segment_id = 1072528 then 1 else 0 end) as righteous,
              sum(case when E.segment_id = 1072528 then E.elapsed_time else 0 end) as righttime,
              sum(case when E.segment_id = 4934241 then 1 else 0 end) as wrongeous,
              sum(case when E.segment_id = 4934241 then E.elapsed_time else 0 end) as wrongtime
            from
              athletes A
            inner join
              rides R on R.athlete_id = A.id
            inner join
              ride_efforts E on E.ride_id = R.id
            group by
              A.id, A.display_name, R.id
         ) as Q
         group by
            Q.id, Q.display_name
         having
            segment_rides > 0
        """
    )
    rs = sess.execute(q)
    retval = [
        (x["id"], x["athlete_name"], x["segment_rides"], x["total_time"])
        for x in rs.fetchall()
    ]
    return sorted(retval, key=operator.itemgetter(2), reverse=True)


@blueprint.route("/rosshillloop")
def ross_hill_loop():
    tdata = _get_ross_hill_loop_tdata()
    return render_template(
        "pointless/rosshillloop.html",
        data={"tdata": tdata},
        meta=meta,
    )


def _get_food_rescue_tdata():
    sess = meta.scoped_session()
    q = text(
        """
        with results as (
            select
                A.id as id,
                A.display_name as athlete_name,
                sum(
                    case when R.name like '%#foodrescuex%' then
                        cast(regexp_replace(R.name, '.*#foodrescuex(\\\\d+).*', '$1') as unsigned)
                    else 1
                    end
                ) AS rescues,
                sum(R.distance) AS distance
            from lbd_athletes A
            join rides R on R.athlete_id = A.id
            where R.name like '%#foodrescue%'
            group by A.id, A.display_name
        )
        select
            R.*,
            rank() over (order by R.rescues desc) AS "rank"
        from results R
        order by R.rescues desc, R.athlete_name asc
        """
    )
    rs = sess.execute(q)
    retval = [
        (x["id"], x["athlete_name"], x["rescues"], x["distance"], x["rank"])
        for x in rs.fetchall()
    ]
    return retval


@blueprint.route("/foodrescue")
def food_rescue():
    tdata = _get_food_rescue_tdata()
    return render_template(
        "pointless/foodrescue.html",
        data={"tdata": tdata},
        meta=meta,
    )


@blueprint.route("/coffeeride")
def coffeeride():
    year = datetime.now().year
    tdata = _get_hashtag_tdata("coffeeride{}".format(year), "coffeeride", 2)
    return render_template(
        "pointless/coffeeride.html", data={"tdata": tdata, "year": year}
    )


@blueprint.route("/pointlesskids")
def pointlesskids():
    q = text(
        """
        select name, distance from rides where upper(name) like '%WITHKID%';
    """
    )
    rs = meta.scoped_session().execute(q)
    d = defaultdict(int)
    for x in rs.fetchall():
        for match in re.findall(r"(#withkid\w+)", x["name"]):
            d[match.replace("#withkid", "")] += x["distance"]
    return render_template(
        "pointless/pointlesskids.html",
        data={"tdata": sorted(d.items(), key=lambda v: v[1], reverse=True)},
    )


@blueprint.route("/kidsathlon")
def kidsathlon():
    q = text(
        """
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
    """
    )
    data = []
    for x in meta.scoped_session().execute(q).fetchall():
        miles_both = float(x["miles_both"])
        kidical = miles_both + float(x["kidical"])
        withkid = miles_both + float(x["withkid"])
        if kidical > 0 and withkid > 0:
            kidsathlon = kidical + withkid - miles_both
        else:
            kidsathlon = float(0)
        data.append((x["athlete_id"], x["athlete_name"], kidical, withkid, kidsathlon))
    return render_template(
        "pointless/kidsathlon.html",
        data={"tdata": sorted(data, key=lambda v: v[4], reverse=True)},
    )


@blueprint.route("/multisegment/<string:leaderboard>")
def multisegment(leaderboard):
    board = load_board(leaderboard)
    data = load_multisegment_board_data(board)
    data.sort(key=lambda d: (-d["segment_rides"], d["athlete_name"]))
    formatted = format_rows(data, board)
    return render_template(
        "pointless/generic.html",
        fields=board.fields,
        title=board.title,
        description=board.description,
        url=board.url,
        data=formatted,
    )


@blueprint.route("/arlington")
def arlington():
    def combine(cw, ccw):
        # if you have ridden no segments of ccw this will report cw as worst but that's okay in my book
        cw_worse = (ccw is None) or (
            cw is not None and cw["segment_rides"] < ccw["segment_rides"]
        )
        return {
            "id": cw["id"] if cw else ccw["id"],
            "athlete_name": cw["athlete_name"] if cw else ccw["athlete_name"],
            "segment_id": cw["segment_id"] if cw_worse else ccw["segment_id"],
            "segment_name": cw["segment_name"] if cw_worse else ccw["segment_name"],
            "segment_rides": (cw["segment_rides"] if cw else 0)
            + (ccw["segment_rides"] if ccw else 0),
        }

    board = load_board("arlington")
    data_cw = {
        d["id"]: d for d in load_multisegment_board_data(load_board("arlington-cw"))
    }
    data_ccw = {
        d["id"]: d for d in load_multisegment_board_data(load_board("arlington-ccw"))
    }
    data = [
        combine(data_cw.get(id), data_ccw.get(id))
        for id in set(data_cw.keys()).union(data_ccw.keys())
    ]
    data.sort(key=lambda d: (-d["segment_rides"], d["athlete_name"]))
    formatted = format_rows(data, board)
    return render_template(
        "pointless/generic.html",
        fields=board.fields,
        title=board.title,
        description=board.description,
        url=board.url,
        data=formatted,
    )


def load_multisegment_board_data(board):
    # include anyone who has ridden on any segment, but count as zero any segment they've missed
    rides = meta.scoped_session().execute(board.query).fetchall()
    # segment_id -> segment_name
    segments = {ride["segment_id"]: ride["segment_name"] for ride in rides}
    # athlete_id -> athlete_name
    athletes = {ride["id"]: ride["athlete_name"] for ride in rides}
    # (athlete_id, segment_id) -> segment_rides
    segment_rides = {
        (ride["id"], ride["segment_id"]): ride["segment_rides"] for ride in rides
    }
    # athlete_id -> segment_id
    worst_segments = {
        id: min(segments.keys(), key=lambda s: segment_rides.get((id, s), 0))
        for id in athletes.keys()
    }
    data = [
        {
            "id": id,
            "athlete_name": athletes[id],
            "segment_id": segment,
            "segment_name": segments[segment],
            "segment_rides": segment_rides.get((id, segment), 0),
        }
        for id, segment in worst_segments.items()
    ]
    return data


@blueprint.route("/daily_variance")
def daily_variance():
    q = text(
        """
        select a.display_name as name, vbd.* from variance_by_day vbd, lbd_athletes a where vbd.athlete_id=a.id
    """
    )
    days_left = (
        config.END_DATE - datetime.now(timezone.utc)
    ).days  # how many days left in the competition
    if days_left < 0:
        days_left = 0
    min_days = 50  # minimum number of ride days to qualify, Chris inititally said 2/3 and this is a nice round number close to 2/3
    data = []
    for x in meta.scoped_session().execute(q).fetchall():
        days_raw = [
            x["mon_var_pop"],
            x["tue_var_pop"],
            x["wed_var_pop"],
            x["thu_var_pop"],
            x["fri_var_pop"],
            x["sat_var_pop"],
            x["sun_var_pop"],
        ]
        days = [x for x in days_raw if x is not None]
        avg = round(sum(days) / len(days), 2)
        qualified = (
            x["ride_days"] + days_left >= min_days
        )  # Either you've ridden enough days or you still can ride enough days
        if qualified and float(x["ride_days"]) > 0:
            qualified = float(x["total_miles"]) / float(x["ride_days"]) > float(
                2.00
            )  # you're averaging more than 2 miles per day you ride
        days_clean = [round(x, 2) if x is not None else "-" for x in days_raw]
        data.append(
            (
                x["athlete_id"],
                x["name"],
                x["ride_days"],
                round(x["total_miles"], 1),
                qualified,
                avg,
            )
            + tuple(days_clean)
        )
    return render_template(
        "pointless/daily_variance.html", data={"tdata": data, "min_days": min_days}
    )


@blueprint.route("/civilwarhistory")
def civilwarhistory():
    q = text(
        """
        select
        A.id as athlete_id,
        A.display_name as athlete_name,
        sum(case when (upper(R.name) like '%#CIVILWARMARKER%') then 1 else 0 end) as markers,
        sum(case when (upper(R.name) like '%#CIVILWARSTREET%') then 1 else 0 end) as streets
        from lbd_athletes A
        join rides R on R.athlete_id = A.id
        where (upper(R.name) like '%#CIVILWARMARKER%' or upper(R.name) like '%#CIVILWARSTREET%')
        group by A.id, A.display_name
    """
    )

    data = []
    for x in meta.scoped_session().execute(q).fetchall():
        markers = x["markers"]
        streets = x["streets"]
        total = (markers * 5) + (streets * 2)
        data.append(
            (
                x["athlete_id"],
                x["athlete_name"],
                markers,
                markers * 5,
                streets,
                streets * 2,
                total,
            )
        )
    return render_template(
        "pointless/civilwarhistory.html",
        data={"tdata": sorted(data, key=lambda v: v[6], reverse=True)},
    )
