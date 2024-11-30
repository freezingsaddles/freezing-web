from setuptools import setup

__authors__ = [
    '"Hans Lellelid" <hans@xmpl.org>',
    "Ian Will",
    "Jon Renaut",
    "Merlin Hughes",
    "Richard Bullington-McGuire <richard.bullington.mcguire@gmail.com>",
    "Adrian Porter",
    "Joe Tatsuko",
]

__copyright__ = "Copyright 2015 Hans Lellelid"

version = "1.5.3"

long_description = """
The freezing saddles cycling competition website/scoreboard.
"""

install_req = [
    "Flask",
    "GeoAlchemy",
    "PyMySQL",
    "PyYAML",
    "alembic",
    "arrow",
    "beautifulsoup4",
    "colorlog",
    "envparse",
    "freezing-model",
    "geojson",
    "gunicorn",
    "marshmallow",
    "marshmallow-enum",
    "polyline",
    "python-instagram",
    "pytz",
    "stravalib",
]

setup(
    name="freezing-web",
    version=version,
    description="Freezing Saddles website component.",
    long_description=long_description,
    author="Hans Lellelid",
    author_email="hans@xmpl.org",
    # This is a workaround for https://github.com/pypa/setuptools/issues/97
    packages=["freezing.web", "freezing.web.views", "freezing.web.utils"],
    # packages=find_packages(include=['freezing.web.*'])
    include_package_data=True,
    package_data={"freezing.web": ["static/*", "templates/*"]},
    license="Apache",
    url="http://github.com/freezingsaddles/freezing-web",
    install_requires=install_req,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
    ],
    # zip_safe=False,
    entry_points="""
        [console_scripts]
        freezing-server = freezing.web.runserver:main
        """,
)
