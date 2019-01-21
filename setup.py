import sys
import os.path
import re
import warnings
import uuid

# Ugh, pip 10 is backward incompatible, but there is a workaround:
# Thanks Stack Overflow https://stackoverflow.com/a/49867265
try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements
from setuptools import setup, find_packages

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2018 Hans Lellelid"

version = '1.1.10'

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
      description="Freezing Saddles website component.",
      long_description=long_description,
      author="Hans Lellelid",
      author_email="hans@xmpl.org",
      # This is a workaround for https://github.com/pypa/setuptools/issues/97
      packages = ['freezing.web', 'freezing.web.views', 'freezing.web.utils'],
      # packages=find_packages(include=['freezing.web.*'])
      include_package_data=True,
      package_data={'freezing.web': ['static/*', 'templates/*']},
      license='Apache',
      url="http://github.com/freezingsaddles/freezing-web",
      install_requires=reqs,
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Apache Software License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 3.6",
                   ],
      #zip_safe=False,
      entry_points="""
        [console_scripts]
        freezing-server = freezing.web.runserver:main
        """,
     )
