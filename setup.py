"""
Library for the Bike Arlington Freezing Saddles (BAFS) competition.
"""
import sys
import os.path
import re
import warnings
import uuid

from pip.req import parse_requirements
from setuptools import setup, find_packages

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2013 Hans Lellelid"

version = '0.2'

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements(os.path.join(os.path.dirname(__file__), 'requirements.txt'), session=uuid.uuid1())

# reqs is a list of requirement
# e.g. ['django==1.5.1', 'mezzanine==1.4.6']
reqs = [str(ir.req) for ir in install_reqs]

news = os.path.join(os.path.dirname(__file__), 'docs', 'news.txt')
news = open(news).read()
parts = re.split(r'([0-9\.]+)\s*\n\r?-+\n\r?', news)
found_news = ''
for i in range(len(parts)-1):
    if parts[i] == version:
        found_news = parts[i+i]
        break
if not found_news:
    warnings.warn('No news for this version found.')

long_description="""
Library for the bike arlington freezing saddles
"""

if found_news:
    title = 'Changes in %s' % version
    long_description += "\n%s\n%s\n" % (title, '-'*len(title))
    long_description += found_news
    
setup(name='bafs',
      version=version,
      description=__doc__,
      long_description=long_description,
      author="Hans Lellelid",
      author_email="hans@xmpl.org",
      packages = find_packages(exclude=['tests', 'ez_setup.py', '*.tests.*', 'tests.*', '*.tests']),
      license='Apache',
      url="http://github.com/hozn/freezing",
      keywords='strava api',
      test_suite="nose.collector",
      tests_require=['nose>=0.11', 'mock'],
      install_requires=reqs,
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Apache Software License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 2.6",
                   "Programming Language :: Python :: 2.7",
                   #"Topic :: Software Development :: Libraries :: Python Modules",
                   ],
      entry_points="""
        [console_scripts]
        bafs-init-db = bafs.scripts.init_db:main
        bafs-sync = bafs.scripts.sync_rides:main
        bafs-sync-detail = bafs.scripts.sync_activity_detail:main
        bafs-sync-photos = bafs.scripts.sync_photos:main
        bafs-sync-weather = bafs.scripts.sync_ride_weather:main
        bafs-sync-athletes = bafs.scripts.sync_athletes:main
        bafs-server = bafs.runserver:main
        bafs-fix-photo-urls = bafs.scripts.fix_photo_urls:main
        """,
     )
