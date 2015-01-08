from datetime import date, timedelta
from datetime import datetime

from flask import render_template, Blueprint, app, send_file
from sqlalchemy import text

from bafs import db
from bafs.model import Team, Athlete
from bafs.utils import insta

blueprint = Blueprint('photos', __name__)

@blueprint.route("/<uid>.jpg")
def instagram_photo(uid):
    photopath = insta.photo_cache_path(uid, resolution=insta.STANDARD)
    return send_file(photopath, mimetype="image/jpeg")

@blueprint.route("/<uid>_thumb.jpg")
def instagram_photo_thumb(uid):
    photopath = insta.photo_cache_path(uid, resolution=insta.THUMBNAIL)
    return send_file(photopath, mimetype="image/jpeg")