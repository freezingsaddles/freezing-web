import json
from datetime import timedelta
from decimal import Decimal

import arrow
import pytz
from flask import Blueprint, jsonify, request, session
from freezing.model import meta
from freezing.model.orm import Athlete, Ride, RidePhoto, RideTrack
from sqlalchemy import text, func

from freezing.web import config
from freezing.web.autolog import log
from freezing.web.serialize import RidePhotoSchema
from freezing.web.utils import auth
from freezing.web.utils.wktutils import parse_linestring

blueprint = Blueprint("api", __name__)


@blueprint.route("/stats/general")
@auth.crossdomain(origin="*")
def stats_general():
    q = text("""select count(*) as num_contestants from lbd_athletes""")

    indiv_count_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    contestant_count = indiv_count_res["num_contestants"]

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time,
                  coalesce(sum(R.distance),0) as distance
                from rides R
                ;
            """
    )

    all_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    total_miles = int(all_res["distance"])
    total_hours = int(all_res["moving_time"]) / 3600
    total_rides = all_res["num_rides"]

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_temp_avg < 32
                ;
            """
    )

    sub32_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    sub_freezing_hours = int(sub32_res["moving_time"]) / 3600

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_rain = 1
                ;
            """
    )

    rain_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    rain_hours = int(rain_res["moving_time"]) / 3600

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_snow = 1
                ;
            """
    )

    snow_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    snow_hours = int(snow_res["moving_time"]) / 3600

    return jsonify(
        team_count=len(config.COMPETITION_TEAMS),
        contestant_count=contestant_count,
        total_rides=total_rides,
        total_hours=total_hours,
        total_miles=total_miles,
        rain_hours=rain_hours,
        snow_hours=snow_hours,
        sub_freezing_hours=sub_freezing_hours,
    )


@blueprint.route("/photos")
@auth.crossdomain(origin="*")
def list_photos():
    photos = (
        meta.scoped_session()
        .query(RidePhoto)
        .join(Ride)
        .order_by(Ride.start_date.desc())
        .limit(20)
    )
    schema = RidePhotoSchema()
    results = []
    for p in photos:
        results.append(schema.dump(p).data)

    return jsonify(dict(result=results, count=len(results)))


@blueprint.route("/leaderboard/team")
@auth.crossdomain(origin="*")
def team_leaderboard():
    """
    Loads the leaderboard data broken down by team.
    """
    q = text(
        """
             select T.id as team_id, T.name as team_name, sum(DS.points) as total_score,
             sum(DS.distance) as total_distance
             from daily_scores DS
             join teams T on T.id = DS.team_id
             where not T.leaderboard_exclude
             group by T.id, T.name
             order by total_score desc
             ;
             """
    )

    team_rows = meta.scoped_session().execute(q).fetchall()  # @UndefinedVariable

    q = text(
        """
             select A.id as athlete_id, A.team_id, A.display_name as athlete_name,
             sum(DS.points) as total_score, sum(DS.distance) as total_distance,
             count(DS.points) as days_ridden
             from daily_scores DS
             join lbd_athletes A on A.id = DS.athlete_id
             group by A.id, A.display_name
             order by total_score desc
             ;
             """
    )

    team_members = {}
    for indiv_row in meta.scoped_session().execute(q).fetchall():  # @UndefinedVariable
        team_members.setdefault(indiv_row["team_id"], []).append(indiv_row)

    for team_id in team_members:
        team_members[team_id] = reversed(
            sorted(team_members[team_id], key=lambda m: m["total_score"])
        )

    rows = []
    for i, res in enumerate(team_rows):
        place = i + 1

        members = [
            {
                "athlete_id": member["athlete_id"],
                "athlete_name": member["athlete_name"],
                "total_score": member["total_score"],
                "total_distance": member["total_distance"],
                "days_ridden": member["days_ridden"],
            }
            for member in team_members.get(res["team_id"], [])
        ]

        rows.append(
            {
                "team_name": res["team_name"],
                "total_score": res["total_score"],
                "total_distance": res["total_distance"],
                "team_id": res["team_id"],
                "rank": place,
                "team_members": members,
            }
        )

    return jsonify(dict(leaderboard=rows))


def _geo_tracks(start_date=None, end_date=None, team_id=None):
    # These dates  must be made naive, since we don't have TZ info stored in our ride columns.
    if start_date:
        start_date = arrow.get(start_date).datetime.replace(tzinfo=None)

    if end_date:
        end_date = arrow.get(end_date).datetime.replace(tzinfo=None)

    log.debug("Filtering on start_date: {}".format(start_date))
    log.debug("Filtering on end_date: {}".format(end_date))

    sess = meta.scoped_session()

    q = (
        sess.query(
            RideTrack, func.ST_AsText(RideTrack.gps_track).label("gps_track_wkt")
        )
        .join(Ride)
        .join(Athlete)
    )
    q = q.filter(~(Ride.private))

    if team_id:
        q = q.filter(Athlete.team_id == team_id)

    if start_date:
        q = q.filter(Ride.start_date >= start_date)
    if end_date:
        q = q.filter(Ride.start_date < end_date)

    linestrings = []
    for ride_track, wkt in q:
        assert isinstance(ride_track, RideTrack)
        assert isinstance(wkt, str)
        ride_tz = pytz.timezone(ride_track.ride.timezone)
        log.info(
            "processing ride_track and wkt",
            extra={"ride_track": ride_track, "wkt": wkt},
        )

        coordinates = []
        for i, (lon, lat) in enumerate(parse_linestring(wkt)):
            elapsed_time = ride_track.ride.start_date + timedelta(
                seconds=ride_track.time_stream[i]
            )

            point = (
                float(Decimal(lon)),
                float(Decimal(lat)),
                float(Decimal(ride_track.elevation_stream[i])),
                ride_tz.localize(elapsed_time).isoformat(),
            )

            coordinates.append(point)

        linestrings.append(coordinates)

    geojson_structure = {"type": "MultiLineString", "coordinates": linestrings}

    return json.dumps(geojson_structure)


@blueprint.route("/all/tracks.geojson")
@auth.crossdomain(origin="*")
def geo_tracks_all():
    log.info("Fetching gps tracks")

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    return _geo_tracks(start_date=start_date, end_date=end_date)


@blueprint.route("/teams/<int:team_id>/tracks.geojson")
@auth.crossdomain(origin="*")
def geo_tracks_team(team_id):
    log.info("Fetching gps tracks for team {}".format(team_id))

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    return _geo_tracks(start_date=start_date, end_date=end_date, team_id=team_id)


# Crude approximation of the distance squared between points
def _distance2(lon0, lat0, lon1, lat1):
    return (lon0 - lon1) * (lon0 - lon1) + (lat0 - lat1) * (lat0 - lat1)


# The maximum "distance squared" to allow between points in a ride track.
# I think in a pretend flat world, this is ~6 miles.
_max_d2 = 0.01


# The full geojson structure is triple the size of what we need
def _track_map(team_id=None, athlete_id=None, include_private=False, hash_tag=None):
    q = text(
        """
             with team_idx(team_id, team_index) as (
                 select id, row_number() over(order by id) from teams
             )
             select ST_AsText(T.gps_track), X.team_index
             from ride_tracks T
             join rides R on R.id = T.ride_id
             join athletes A on A.id = R.athlete_id
             join team_idx X on X.team_id = A.team_id
             where
             {0} and {1} and {2} and {3}
             order by R.start_date DESC
             limit 1024
             ;
             """.format(
            "true" if include_private else "not(R.private)",
            "A.id = :athlete_id" if athlete_id else "true",
            "A.team_id = :team_id" if team_id else "true",
            "R.name like :hash_tag" if hash_tag else "true",
        )
    )

    if team_id:
        q = q.bindparams(team_id=team_id)
    if athlete_id:
        q = q.bindparams(athlete_id=athlete_id)
    if hash_tag:
        q = q.bindparams(hash_tag="%#{}%".format(hash_tag))

    tracks = []
    for [gps_track, team_id] in meta.scoped_session().execute(q).fetchall():
        track = []
        tracks.append({"team": team_id, "track": track})
        point = None
        for _, (lons, lats) in enumerate(parse_linestring(gps_track)):
            lon = float(Decimal(lons))
            lat = float(Decimal(lats))
            # Break tracks that span flights and train journeys
            if point and _distance2(lon, lat, point[0], point[1]) > _max_d2:
                track = []
                tracks.append({"team": team_id, "track": track})
            point = (lon, lat)
            track.append(point)
    tracks.reverse()

    return {"tracks": tracks}


@blueprint.route("/all/trackmap.json")
def track_map_all():
    hash_tag = request.args.get("hashtag")
    return jsonify(_track_map(hash_tag=hash_tag))


@blueprint.route("/my/trackmap.json")
@auth.requires_auth
def track_map_my():
    athlete_id = session.get("athlete_id")
    return jsonify(_track_map(athlete_id=athlete_id, include_private=True))


@blueprint.route("/teams/<int:team_id>/trackmap.json")
def track_map_team(team_id):
    return jsonify(_track_map(team_id=team_id))
