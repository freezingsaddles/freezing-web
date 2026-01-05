import json
import logging
from datetime import datetime
import arrow

from flask import Blueprint, current_app, jsonify, render_template, request, session
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
                avg_temp=avg_temp,
                distance=r.distance,
                elapsed_time=r.elapsed_time,
                id=r.id,
                moving_time=r.moving_time,
                duration_human=arrow.utcnow().shift(seconds=-int(r.moving_time)).humanize(only_distance=True),                name=r.name,
                photos_fetched=r.photos_fetched,
                private=r.private,
                start_date=r.start_date,
            )
        )
    return bt_jsonify(results)
