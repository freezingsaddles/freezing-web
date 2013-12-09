"""
Library for the Bike Arlington Freezing Saddles (BAFS) competition.
"""
import sys
import os.path
import re
import warnings

from setuptools import setup, find_packages

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2013 Hans Lellelid"

version = '0.2'

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
      install_requires=['requests',
                        'stravalib>=0.2',
                        'SQLAlchemy',
                        'alembic',
                        'GeoAlchemy',
                        'MySQL-python',
                        'pytz',
                        'python-dateutil{0}'.format('>=2.0,<3.0dev' if sys.version_info[0] == 3 else '>=1.5,<2.0dev'), # version 1.x is for python 2 and version 2.x is for python 3.
                        'beautifulsoup4',
                        'Flask',
                        'Flask-SQLAlchemy',
                        'pytz',
                        'colorlog'],
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
        bafs-init-db = bafs.scripts:init_db
        bafs-sync = bafs.scripts:sync_rides
        bafs-sync-weather = bafs.scripts:sync_ride_weather
        bafs-server = bafs.runserver:main
        """,
     )
