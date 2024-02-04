#!/usr/bin/env python3
import sys
import os
import logging

"""
This is a file designed to be used with Phusion Passenger.

Move this file into the directory above your 'public' directory.

We assume this repository is part of the
(This file is not intended for use when using freezing-web in Docker container.)
"""


BASE_DIR = os.path.join(os.path.dirname(__file__))
INTERP = os.path.join(BASE_DIR, "env", "bin", "python")
# This trick causes a reload using our correct python environment
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)
sys.path.append(os.path.join(BASE_DIR, "bafs"))

os.environ["APP_SETTINGS"] = os.path.join(BASE_DIR, "settings.cfg")

from freezing.web import app as application  # noqa

ch = logging.FileHandler(os.path.join(BASE_DIR, "application.log"))
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s")
ch.setFormatter(formatter)

loggers = [
    application.logger,
    logging.getLogger("stravalib"),
    logging.getLogger("requests"),
    logging.root,
]

for logger in loggers:
    logger.setLevel(logging.INFO)
    logger.addHandler(ch)

# Uncomment next two lines to enable debugging
# from werkzeug.debug import DebuggedApplication
# application = DebuggedApplication(application, evalex=True)
