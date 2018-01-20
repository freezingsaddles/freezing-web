import sys
import os.path
import re
import warnings
import uuid

from pip.req import parse_requirements
from setuptools import setup, find_packages

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2018 Hans Lellelid"

version = '1.0'

long_description="""
The freezing saddles cycling competition website/scoreboard.
"""

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements(os.path.join(os.path.dirname(__file__), 'requirements.txt'), session=uuid.uuid1())

# reqs is a list of requirement
# e.g. ['django==1.5.1', 'mezzanine==1.4.6']
reqs = [str(ir.req) for ir in install_reqs]


setup(name='freezing-web',
      version=version,
      description=__doc__,
      long_description=long_description,
      author="Hans Lellelid",
      author_email="hans@xmpl.org",
      packages = find_packages(exclude=['tests', 'ez_setup.py', '*.tests.*', 'tests.*', '*.tests']),
      license='Apache',
      url="http://github.com/freezingsaddles/freezing-web",
      keywords='strava api',
      test_suite="nose.collector",
      tests_require=['nose>=0.11', 'mock'],
      install_requires=reqs,
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Apache Software License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 3.6",
                   ],
      entry_points="""
        [console_scripts]
        bafs-init-db = freezing.web.scripts.init_db:main
        bafs-sync = freezing.web.scripts.sync_rides:main
        bafs-sync-detail = freezing.web.scripts.sync_activity_detail:main
        bafs-sync-streams = freezing.web.scripts.sync_streams:main
        bafs-sync-photos = freezing.web.scripts.sync_photos:main
        bafs-sync-weather = freezing.web.scripts.sync_ride_weather:main
        bafs-sync-athletes = freezing.web.scripts.sync_athletes:main
        bafs-server = freezing.web.runserver:main
        bafs-fix-photo-urls = freezing.web.scripts.fix_photo_urls:main
        """,
     )
