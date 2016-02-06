from datetime import timedelta
from decimal import Decimal
import json

import arrow
import geojson
from flask import Blueprint, jsonify, request
import pytz
from sqlalchemy import text
from stravalib import unithelper as uh

from bafs import app, db
from bafs.autolog import log
from bafs.model import RidePhoto, Ride, RideTrack, Athlete
from bafs.serialize import RidePhotoSchema
from bafs.utils import auth, dates
from bafs.utils.wktutils import parse_linestring

blueprint = Blueprint('api', __name__)


@blueprint.route("/stats/general")
@auth.crossdomain(origin='*')
def stats_general():
    q = text("""select count(*) as num_contestants from athletes WHERE team_id is not null""")

    indiv_count_res = db.session.execute(q).fetchone()  # @UndefinedVariable
    contestant_count = indiv_count_res['num_contestants']

    q = text("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time,
                  coalesce(sum(R.distance),0) as distance
                from rides R
                ;
            """)

    all_res = db.session.execute(q).fetchone()  # @UndefinedVariable
    total_miles = int(all_res['distance'])
    total_hours = uh.timedelta_to_seconds(timedelta(seconds=int(all_res['moving_time']))) / 3600
    total_rides = all_res['num_rides']

    q = text("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_temp_avg < 32
                ;
            """)

    sub32_res = db.session.execute(q).fetchone()  # @UndefinedVariable
    sub_freezing_hours = uh.timedelta_to_seconds(timedelta(seconds=int(sub32_res['moving_time']))) / 3600

    q = text("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_rain = 1
                ;
            """)

    rain_res = db.session.execute(q).fetchone()  # @UndefinedVariable
    rain_hours = uh.timedelta_to_seconds(timedelta(seconds=int(rain_res['moving_time']))) / 3600

    q = text("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_snow = 1
                ;
            """)

    snow_res = db.session.execute(q).fetchone()  # @UndefinedVariable
    snow_hours = uh.timedelta_to_seconds(timedelta(seconds=int(snow_res['moving_time']))) / 3600

    return jsonify(
            team_count=len(app.config['BAFS_TEAMS']),
            contestant_count=contestant_count,
            total_rides=total_rides,
            total_hours=total_hours,
            total_miles=total_miles,
            rain_hours=rain_hours,
            snow_hours=snow_hours,
            sub_freezing_hours=sub_freezing_hours)


@blueprint.route("/photos")
@auth.crossdomain(origin='*')
def list_photos():
    photos = db.session.query(RidePhoto).join(Ride).order_by(Ride.start_date.desc()).limit(20)
    schema = RidePhotoSchema()
    results = []
    for p in photos:
        results.append(schema.dump(p).data)

    return jsonify(dict(result=results, count=len(results)))


@blueprint.route("/leaderboard/team")
@auth.crossdomain(origin='*')
def team_leaderboard():
    """
    Loads the leaderboard data broken down by team.
    """
    q = text("""
             select T.id as team_id, T.name as team_name, sum(DS.points) as total_score,
             sum(DS.distance) as total_distance
             from daily_scores DS
             join teams T on T.id = DS.team_id
             group by T.id, T.name
             order by total_score desc
             ;
             """)

    team_rows = db.session.execute(q).fetchall()  # @UndefinedVariable

    q = text("""
             select A.id as athlete_id, A.team_id, A.display_name as athlete_name,
             sum(DS.points) as total_score, sum(DS.distance) as total_distance,
             count(DS.points) as days_ridden
             from daily_scores DS
             join athletes A on A.id = DS.athlete_id
             group by A.id, A.display_name
             order by total_score desc
             ;
             """)

    team_members = {}
    for indiv_row in db.session.execute(q).fetchall():  # @UndefinedVariable
        team_members.setdefault(indiv_row['team_id'], []).append(indiv_row)

    for team_id in team_members:
        team_members[team_id] = reversed(sorted(team_members[team_id], key=lambda m: m['total_score']))

    rows = []
    for i, res in enumerate(team_rows):
        place = i + 1

        members = [{'athlete_id': member['athlete_id'],
                    'athlete_name': member['athlete_name'],
                    'total_score': member['total_score'],
                    'total_distance': member['total_distance'],
                    'days_ridden': member['days_ridden']}
                   for member in team_members.get(res['team_id'], [])]

        rows.append({
            'team_name': res['team_name'],
            'total_score': res['total_score'],
            'total_distance': res['total_distance'],
            'team_id': res['team_id'],
            'rank': place,
            'team_members': members
        })

    return jsonify(dict(leaderboard=rows))

@blueprint.route("/teams/<int:team_id>/tracks.geojson")
@auth.crossdomain(origin='*')
def geo_tracks(team_id):

    # log.info("Fetching gps tracks for team {}".format(team_id))

    start_date = request.args.get('start_date')
    if start_date:
        #start_date = dates.parse_competition_timestamp(start_date)
        start_date = arrow.get(start_date).datetime.replace(tzinfo=None)

    end_date = request.args.get('end_date')
    if end_date:
        #end_date = dates.parse_competition_timestamp(end_date)
        end_date = arrow.get(end_date).datetime.replace(tzinfo=None)

    log.info("Filtering on start_date: {}".format(start_date))

    sess = db.session

    q = sess.query(RideTrack).join(Ride).join(Athlete).filter(Athlete.team_id==team_id)
    if start_date:
        q = q.filter(Ride.start_date >= start_date)
    if end_date:
        q = q.filter(Ride.start_date < end_date)

    linestrings = []
    for ride_track in q:
        assert isinstance(ride_track, RideTrack)
        wkt = sess.scalar(ride_track.gps_track.wkt)

        coordinates = []
        for (i, (lon, lat)) in enumerate(parse_linestring(wkt)):
            localized_dt = ride_track.ride.start_date.replace(tzinfo=pytz.timezone(ride_track.ride.timezone))
            elapsed_time = localized_dt + timedelta(seconds=ride_track.time_stream[i])

            point = (
                Decimal(lon),
                Decimal(lat),
                Decimal(ride_track.elevation_stream[i]),
                elapsed_time.isoformat()
            )

            coordinates.append(point)

        linestrings.append(coordinates)

    return geojson.dumps(geojson.MultiLineString(linestrings))
