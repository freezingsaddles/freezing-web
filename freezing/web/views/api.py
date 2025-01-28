import datetime
import gzip
import hashlib
import json
import os
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import arrow
import pytz
from flask import Blueprint, abort, jsonify, make_response, request, session
from freezing.model import meta
from freezing.model.orm import Athlete, Ride, RidePhoto, RideTrack
from sqlalchemy import func, text
from werkzeug.utils import secure_filename

from freezing.web import config
from freezing.web.autolog import log
from freezing.web.serialize import RidePhotoSchema
from freezing.web.utils import auth
from freezing.web.utils.wktutils import parse_linestring, parse_point_wkt

blueprint = Blueprint("api", __name__)


def get_limit(request):
    """Get the limit parameter from the request, if it exists.

    Impose a maximum limit on the number of tracks to return.
    This is a safety measure to mitigate denial of service attacks.
    Geojson APIs can return 1024 entries in <5 seconds.

    See: Geojson APIs suspeculatively not scalable #310
    https://github.com/freezingsaddles/freezing-web/issues/310
    """
    limit = request.args.get("limit")
    if limit is None:
        return config.TRACK_LIMIT_DEFAULT
    limit = int(limit)
    if limit > config.TRACK_LIMIT_MAX:
        abort(400, f"limit {limit} exceeds {config.TRACK_LIMIT_MAX}")
    return min(config.TRACK_LIMIT_MAX, int(limit))


@blueprint.route("/stats/general")
@auth.crossdomain(origin="*")
def stats_general():
    q = text("""select count(*) as num_contestants from lbd_athletes""")

    indiv_count_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    contestant_count = indiv_count_res._mapping["num_contestants"]

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time,
                  coalesce(sum(R.distance),0) as distance
                from rides R
                ;
            """
    )

    all_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    total_miles = int(all_res._mapping["distance"])
    total_hours = int(all_res._mapping["moving_time"]) / 3600
    total_rides = all_res._mapping["num_rides"]

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
    sub_freezing_hours = int(sub32_res._mapping["moving_time"]) / 3600

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
    rain_hours = int(rain_res._mapping["moving_time"]) / 3600

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
    snow_hours = int(snow_res._mapping["moving_time"]) / 3600

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
            for member in team_members.get(res._mapping["team_id"], [])
        ]

        rows.append(
            {
                "team_name": res._mapping["team_name"],
                "total_score": res._mapping["total_score"],
                "total_distance": res._mapping["total_distance"],
                "team_id": res._mapping["team_id"],
                "rank": place,
                "team_members": members,
            }
        )

    return jsonify(dict(leaderboard=rows))


def _geo_tracks(start_date=None, end_date=None, team_id=None, limit=None):
    # These dates  must be made naive, since we don't have TZ info stored in our ride columns.
    if start_date is not None:
        start_date = arrow.get(start_date).datetime.replace(tzinfo=None)

    if end_date is not None:
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

    if team_id is not None:
        q = q.filter(Athlete.team_id == team_id)

    if start_date is not None:
        q = q.filter(Ride.start_date >= start_date)
    if end_date is not None:
        q = q.filter(Ride.start_date < end_date)

    if limit is not None:
        q = q.limit(limit)

    # Note this does not respect privacy but we do not currently display this.
    linestrings = []
    log.debug(f"Querying for tracks: {q}")
    for ride_track, wkt in q:
        assert isinstance(ride_track, RideTrack)
        assert isinstance(wkt, str)
        ride_tz = pytz.timezone(ride_track.ride.timezone)

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
    limit = get_limit(request)

    return _geo_tracks(start_date=start_date, end_date=end_date, limit=limit)


@blueprint.route("/teams/<int:team_id>/tracks.geojson")
@auth.crossdomain(origin="*")
def geo_tracks_team(team_id):
    log.info("Fetching gps tracks for team {}".format(team_id))

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    limit = get_limit(request)

    return _geo_tracks(
        start_date=start_date, end_date=end_date, team_id=team_id, limit=limit
    )


# Crude approximation of the distance squared between points
def _distance2(lon0, lat0, lon1, lat1):
    return (lon0 - lon1) * (lon0 - lon1) + (lat0 - lat1) * (lat0 - lat1)


# The maximum "distance squared" to allow between points in a ride track.
# I think in a pretend flat world, this is ~6 miles.
_max_contiguous2 = 0.01

# The "distance squared" to prune from the start and end of tracks for
# privacy reasons. ~.2 miles?
_min_privacy2 = 0.00001


def _parse_point(wkt):
    point = parse_point_wkt(wkt)
    return (float(Decimal(point.lon)), float(Decimal(point.lat)))


# The full geojson structure is triple the size of what we need
def _track_map(
    team_id=None,
    athlete_id=None,
    include_private=False,
    hash_tag=None,
    ride_ids=None,
    limit=None,
):
    teamsq = text("select id, name from teams order by id asc")
    teams = [
        {"id": id, "name": name}
        for [id, name] in meta.scoped_session().execute(teamsq).fetchall()
    ]

    q = text(
        f"""
             select ST_AsText(T.gps_track), ST_AsText(G.start_geo), ST_AsText(G.end_geo), A.team_id
             from ride_tracks T
             join ride_geo G on G.ride_id = T.ride_id
             join rides R on R.id = T.ride_id
             join athletes A on A.id = R.athlete_id
             where
               {'true' if include_private else 'not(R.private)'}
               and {'A.id = :athlete_id' if athlete_id else 'true'}
               and {'A.team_id = :team_id' if team_id else 'true'}
               and {'R.name like :hash_tag' if hash_tag else 'true'}
               and {'FIND_IN_SET(hex(R.id), :ride_ids) > 0' if ride_ids else 'true'}
             order by R.start_date DESC
             {'limit :limit' if limit else ''}
             """
    )

    if team_id:
        q = q.bindparams(team_id=team_id)
    if athlete_id:
        q = q.bindparams(athlete_id=athlete_id)
    if hash_tag:
        q = q.bindparams(hash_tag="%#{}%".format(hash_tag))
    if ride_ids:
        q = q.bindparams(ride_ids=ride_ids)
    if limit:
        q = q.bindparams(limit=limit)

    # Be warned, the terms "lon" and lat" in the following code should not be read as longitude and
    # latitude. There is confusion about which order these fields occur in the database; it has
    # varied from year to year.
    tracks = []
    for [gps_track, start_geowkt, end_geowkt, team_id] in (
        meta.scoped_session().execute(q).fetchall()
    ):
        start_geo = _parse_point(start_geowkt)
        end_geo = _parse_point(end_geowkt)

        track_points = [
            (float(Decimal(lon)), float(Decimal(lat)))
            for (lon, lat) in parse_linestring(gps_track)
        ]

        # Trim points from the start and end that are within a short distance of the actual ride start
        # and end locations, because Strava sometimes feeds us geometry within riders' privacy radii
        # and they do not wish these data to be shown. This will not hide a mid-ride stop back home, but
        # Strava does not hide this either.
        while (
            track_points
            and _distance2(
                track_points[0][0], track_points[0][1], start_geo[0], start_geo[1]
            )
            < _min_privacy2
        ):
            del track_points[0]
        while (
            track_points
            and _distance2(
                track_points[-1][0], track_points[-1][1], end_geo[0], end_geo[1]
            )
            < _min_privacy2
        ):
            del track_points[-1]

        track = None
        point = None
        for lat, lon in track_points:
            # Break tracks that span flights and train journeys
            if not point or _distance2(lon, lat, point[0], point[1]) > _max_contiguous2:
                track = []
                tracks.append({"team": team_id, "track": track})
            point = (lon, lat)
            track.append(point)
    tracks.reverse()

    return {"tracks": tracks, "teams": teams}


def _get_cached(key: str, compute):
    cache_dir = config.JSON_CACHE_DIR
    if not cache_dir:
        return compute()

    sanitized_key = secure_filename(key)
    cache_file = Path(
        os.path.normpath(Path(cache_dir).joinpath(sanitized_key))
    ).resolve()
    try:
        if os.path.commonpath([str(cache_file), str(Path(cache_dir).resolve())]) != str(
            Path(cache_dir).resolve()
        ):
            raise Exception("Invalid cache file path")
        if cache_file.is_file():
            time_stamp = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
            age = datetime.datetime.now() - time_stamp
            if age.total_seconds() < config.JSON_CACHE_MINUTES * 60:
                return cache_file.read_bytes()

        content = compute()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        if os.path.commonpath([str(cache_file), str(Path(cache_dir).resolve())]) != str(
            Path(cache_dir).resolve()
        ):
            raise Exception("Invalid cache file path")
        cache_file.write_bytes(content)

        return content
    except Exception as e:
        err = f"Error retrieving cached item {sanitized_key}: {e}"
        log.exception(err)
        abort(500, err)


def _make_gzip_json_response(content, private=False):
    response = make_response(content)
    response.headers["Content-Length"] = len(content)
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Type"] = "application/json"
    response.headers["Cache-Control"] = (
        f"max-age={config.JSON_CACHE_MINUTES * 60}, {'private' if private else 'public'}"
    )
    return response


@blueprint.route("/all/trackmap.json")
def track_map_all():
    hash_tag = request.args.get("hashtag")
    ride_ids = request.args.get("rides")
    limit = get_limit(request)

    key_str = hash_tag or ride_ids
    key = (
        hashlib.md5(key_str.encode("utf-8"), usedforsecurity=False) if key_str else None
    )
    return _make_gzip_json_response(
        _get_cached(
            (
                f"track_map/all/{key}-{limit}.json.gz"
                if key
                else f"track_map/all/{limit}.json.gz"
            ),
            lambda: gzip.compress(
                json.dumps(
                    _track_map(hash_tag=hash_tag, limit=limit, ride_ids=ride_ids),
                    indent=None,
                ).encode("utf8"),
                5,
            ),
        )
    )


@blueprint.route("/my/trackmap.json")
@auth.requires_auth
def track_map_my():
    athlete_id = session.get("athlete_id")
    limit = get_limit(request)

    return _make_gzip_json_response(
        _get_cached(
            f"track_map/athlete/{athlete_id}-{limit}.json.gz",
            lambda: gzip.compress(
                json.dumps(
                    _track_map(
                        athlete_id=athlete_id, include_private=True, limit=limit
                    ),
                    indent=None,
                ).encode("utf8"),
                5,
            ),
        ),
        private=True,
    )


@blueprint.route("/teams/<int:team_id>/trackmap.json")
def track_map_team(team_id: int):
    limit = get_limit(request)

    return _make_gzip_json_response(
        _get_cached(
            f"track_map/team/{team_id}-{limit}.json.gz",
            lambda: gzip.compress(
                json.dumps(
                    _track_map(team_id=team_id, limit=limit), indent=None
                ).encode("utf8"),
                5,
            ),
        )
    )
