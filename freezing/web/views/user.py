import json
import logging
from datetime import datetime

from flask import render_template, current_app, request, Blueprint, session, jsonify

from freezing.model import meta
from freezing.model.orm import Ride

from freezing.web.utils.auth import requires_auth


def bt_jsonify(data):
    """
    Override eto handle raw lists expected by bootrap table.
    """
    return current_app.response_class(
        json.dumps(data, default=json_seralizer), mimetype="application/json"
    )


blueprint = Blueprint("user", __name__)


def json_seralizer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return str(obj)


@blueprint.route("/rides")
@requires_auth
def rides():
    return render_template("user/rides.html")


@blueprint.route("/refetch_ride_photos", methods=["POST"])
@requires_auth
def ride_refetch_photos():
    ride_id = request.form["id"]
    ride = (
        meta.scoped_session()
        .query(Ride)
        .filter(Ride.id == ride_id)
        .filter(Ride.athlete_id == session.get("athlete_id"))
        .one()
    )
    ride.photos_fetched = False
    logging.info("Marking photos to be refetched for ride {}".format(ride))
    meta.scoped_session().commit()
    return jsonify(success=True)  # I don't really have anything useful to spit back.


@blueprint.route("/rides.json")
@requires_auth
def rides_data():
    athlete_id = session.get("athlete_id")

    rides_q = (
        meta.scoped_session()
        .query(Ride)
        .filter(Ride.athlete_id == athlete_id)
        .order_by(Ride.start_date.desc())
    )
    results = []

    for r in rides_q:
        w = r.weather
        if w:
            avg_temp = w.ride_temp_avg
        else:
            avg_temp = None

        results.append(
            dict(
                id=r.id,
                private=r.private,
                name=r.name,
                start_date=r.start_date,
                elapsed_time=r.elapsed_time,
                moving_time=r.moving_time,
                distance=r.distance,
                photos_fetched=r.photos_fetched,
                avg_temp=avg_temp,
            )
        )

    # rides = meta.session_factory().query(Ride).all()
    return bt_jsonify(results)


#     athlete_id = sa.Column(sa.BigInteger, sa.ForeignKey('athletes.id', ondelete='cascade'), nullable=False, index=True)
#     elapsed_time = sa.Column(sa.Integer, nullable=False) # Seconds
#     # in case we want to conver that to a TIME type ... (using time for interval is kinda mysql-specific brokenness, though)
#     # time.strftime('%H:%M:%S', time.gmtime(12345))
#     moving_time = sa.Column(sa.Integer, nullable=False, index=True) #
#     elevation_gain = sa.Column(sa.Integer, nullable=True) # 269.6 (feet)
#     average_speed = sa.Column(sa.Float) # mph
#     maximum_speed = sa.Column(sa.Float) # mph
#     start_date = sa.Column(sa.DateTime, nullable=False, index=True) # 2010-02-28T08:31:35Z
#     distance = sa.Column(sa.Float, nullable=False, index=True) # 82369.1 (meters)
#     location = sa.Column(sa.String(255), nullable=True)
#
#     commute = sa.Column(sa.Boolean, nullable=True)
#     trainer = sa.Column(sa.Boolean, nullable=True)
#
#     efforts_fetched = sa.Column(sa.Boolean, default=False, nullable=False)
#
#     timezone = sa.Column(sa.String(255), nullable=True)
#
#     geo = orm.relationship("RideGeo", uselist=False, backref="ride", cascade="all, delete, delete-orphan")
#     weather = orm.relationship("RideWeather", uselist=False, backref="ride", cascade="all, delete, delete-orphan")
#     photos = orm.relationship("RidePhoto", backref="ride", cascade="all, delete, delete-orphan")
#
#     photos_fetched = sa.Column(sa.Boolean, default=False, nullable=False)
#     private = sa.Column(sa.Boolean, default=False, nullable=False)
