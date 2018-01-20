import math
from datetime import date, timedelta
from datetime import datetime

from flask import render_template, Blueprint, app, send_file, request
from sqlalchemy import text

from freezing.model import meta
from freezing.model.orm import Team, Athlete, RidePhoto, Ride

from freezing.web.utils import insta
from freezing.web.autolog import log

blueprint = Blueprint('photos', __name__)

@blueprint.route("/<uid>.jpg")
def instagram_photo(uid):
    photopath = insta.photo_cache_path(uid, resolution=insta.STANDARD)
    return send_file(photopath, mimetype="image/jpeg")

@blueprint.route("/<uid>_thumb.jpg")
def instagram_photo_thumb(uid):
    photopath = insta.photo_cache_path(uid, resolution=insta.THUMBNAIL)
    return send_file(photopath, mimetype="image/jpeg")

@blueprint.route("/")
def index():
    page = int(request.args.get('page', 1))
    if page < 1:
        page = 1

    page_size = 60
    offset = page_size * (page - 1)
    limit = page_size

    log.debug("Page = {0}, offset={1}, limit={2}".format(page, offset, limit))

    total_q = meta.session_factory().query(RidePhoto).join(Ride).order_by(Ride.start_date.desc())
    num_photos = total_q.count()

    page_q = total_q.limit(limit).offset(offset)

    if num_photos < offset:
        page = 1

    total_pages = int(math.ceil( (1.0 * num_photos) / page_size))

    if page > total_pages:
        page = total_pages

    return render_template('photos.html',
                           photos=page_q,
                           page=page,
                           total_pages=total_pages)