"""
Utility functions for working with images.
"""

import os
import urllib
import shutil

from instagram.client import InstagramAPI
from freezing.web import app, exc
from freezing.web.config import config

THUMBNAIL_DIMS = (150, 150)
STANDARD_DIMS = (640, 640)
LOW_DIMS = (306, 306)

IMG_FNAME_TPL = "{uid}.jpg"

STANDARD = "standard_resolution"
THUMBNAIL = "thumbnail"
LOW = "low_resolution"


def configured_instagram_client():
    """
    Get the configured Instagram client.

    :return: Instagram with configured client ID.
    :rtype: instagram.client.InstagramAPI
    """
    return InstagramAPI(client_id=config.INSTAGRAM_CLIENT_ID)


def photo_cache_path(uid, resolution=STANDARD):
    assert resolution in (STANDARD, THUMBNAIL, LOW)
    cache_dir = config.INSTAGRAM_CACHE_DIR
    if not cache_dir:
        raise exc.ConfigurationError("INSTAGRAM_CACHE_DIR not configured!")

    photo_fname = IMG_FNAME_TPL.format(uid=uid)
    cache_path = os.path.join(cache_dir, resolution, photo_fname)
    if not os.path.exists(cache_path):
        cache_photos(uid, base_dir=cache_dir)
    # We expect that if that executed without errors then our path is now valid
    assert os.path.exists(cache_path)
    return cache_path


def cache_photos(uid, base_dir):
    api = configured_instagram_client()

    mediaobj = api.media(uid)

    for res in ("standard_resolution", "low_resolution", "thumbnail"):
        photo = mediaobj.images[res]
        _write_instagram_photo(
            uid=uid, photo=photo, dest_dir=os.path.join(base_dir, res)
        )


def cache_photos(uid, base_dir):
    api = configured_instagram_client()

    mediaobj = api.media(uid)

    for res in ("standard_resolution", "low_resolution", "thumbnail"):
        photo = mediaobj.images[res]
        _write_instagram_photo(
            uid=uid, photo=photo, dest_dir=os.path.join(base_dir, res)
        )


def _write_instagram_photo(uid, photo, dest_dir):
    """
    Writes out photo for specified uid and Image object to destination directory.
    :param uid:
    :param photo:
    :param dest_dir:
    :return:
    """
    photo_fname = IMG_FNAME_TPL.format(uid=uid)
    (filename, headers) = urllib.urlretrieve(photo.url)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    shutil.move(filename, os.path.join(dest_dir, photo_fname))
