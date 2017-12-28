import re
import warnings
import json

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import Pool
from sqlalchemy.sql.expression import Executable, ClauseElement
from sqlalchemy.types import TypeDecorator, TEXT

import geoalchemy as ga
from bafs import db


class JSONEncodedText(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Usage::

        JSONEncodedText
    """

    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class CreateView(Executable, ClauseElement):
    def __init__(self, name, select):
        self.name = name
        self.select = select


@compiles(CreateView, 'mysql')
def visit_create_view(element, compiler, **kw):
    return "CREATE VIEW IF NOT EXISTS %s AS %s" % (
        element.name,
        compiler.process(element.select, literal_binds=True)
    )


class StravaEntity(db.Model):
    __abstract__ = True
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}  # But we use MyISAM for the spatial table.

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=False)
    name = sa.Column(sa.String(1000), nullable=False)

    def __init__(self, id=None, name=None, **kwargs):
        self.id = id
        self.name = name
        for (k, v) in kwargs.items():
            try:
                setattr(self, k, v)
            except AttributeError:
                raise AttributeError("Unable to set attribute {0} on {1}".format(k, self.__class__.__name__))

    def __repr__(self):
        return '<{0} id={1} name={2!r}>'.format(self.__class__.__name__, self.id, self.name)


class Team(StravaEntity):
    """
    """
    __tablename__ = 'teams'
    athletes = orm.relationship("Athlete", backref="team")
    leaderboard_exclude = sa.Column(sa.Boolean, nullable=False, default=False)

class Athlete(StravaEntity):
    """
    """
    __tablename__ = 'athletes'
    display_name = sa.Column(sa.String(255), nullable=True)
    team_id = sa.Column(sa.BigInteger, sa.ForeignKey('teams.id', ondelete='set null'))
    access_token = sa.Column(sa.String(255), nullable=True)
    profile_photo = sa.Column(sa.String(255), nullable=True)

    rides = orm.relationship("Ride", backref="athlete", lazy="dynamic", cascade="all, delete, delete-orphan")


class RideError(StravaEntity):
    """
    """
    __tablename__ = 'ride_errors'
    athlete_id = sa.Column(sa.BigInteger, sa.ForeignKey('athletes.id', ondelete='cascade'), nullable=False, index=True)
    start_date = sa.Column(sa.DateTime, nullable=False, index=True)  # 2010-02-28T08:31:35Z
    last_seen = sa.Column(sa.DateTime, nullable=False, index=True)
    reason = sa.Column(sa.String(1024), nullable=False)


class Ride(StravaEntity):
    """
    """
    __tablename__ = 'rides'
    athlete_id = sa.Column(sa.BigInteger, sa.ForeignKey('athletes.id', ondelete='cascade'), nullable=False, index=True)
    elapsed_time = sa.Column(sa.Integer, nullable=False)  # Seconds
    # in case we want to conver that to a TIME type ... (using time for interval is kinda mysql-specific brokenness, though)
    # time.strftime('%H:%M:%S', time.gmtime(12345))
    moving_time = sa.Column(sa.Integer, nullable=False, index=True)  #
    elevation_gain = sa.Column(sa.Integer, nullable=True)  # 269.6 (feet)
    average_speed = sa.Column(sa.Float)  # mph
    maximum_speed = sa.Column(sa.Float)  # mph
    start_date = sa.Column(sa.DateTime, nullable=False, index=True)  # 2010-02-28T08:31:35Z
    distance = sa.Column(sa.Float, nullable=False, index=True)  # 82369.1 (meters)
    location = sa.Column(sa.String(255), nullable=True)

    commute = sa.Column(sa.Boolean, nullable=True)
    trainer = sa.Column(sa.Boolean, nullable=True)

    efforts_fetched = sa.Column(sa.Boolean, default=False, nullable=False)

    timezone = sa.Column(sa.String(255), nullable=True)

    geo = orm.relationship("RideGeo", uselist=False, backref="ride", cascade="all, delete, delete-orphan")
    weather = orm.relationship("RideWeather", uselist=False, backref="ride", cascade="all, delete, delete-orphan")
    photos = orm.relationship("RidePhoto", backref="ride", cascade="all, delete, delete-orphan")
    track = orm.relationship("RideTrack", uselist=False, backref="ride", cascade="all, delete, delete-orphan")

    photos_fetched = sa.Column(sa.Boolean, default=None, nullable=True)
    track_fetched = sa.Column(sa.Boolean, default=None, nullable=True)
    detail_fetched = sa.Column(sa.Boolean, default=False, nullable=False)

    private = sa.Column(sa.Boolean, default=False, nullable=False)
    manual = sa.Column(sa.Boolean, default=None, nullable=True)


# Broken out into its own table due to MySQL (5.0/1.x, anyway) not allowing NULL values in geometry columns.
class RideGeo(db.Model):
    __tablename__ = 'ride_geo'
    __table_args__ = {'mysql_engine': 'MyISAM', 'mysql_charset': 'utf8'}  # MyISAM for spatial indexes

    ride_id = sa.Column(sa.BigInteger, sa.ForeignKey('rides.id'), primary_key=True)
    start_geo = ga.GeometryColumn(ga.Point(2), nullable=False)
    end_geo = ga.GeometryColumn(ga.Point(2), nullable=False)

    def __repr__(self):
        return '<{0} ride_id={1} start={2}>'.format(self.__class__.__name__,
                                                    self.ride_id,
                                                    self.start_geo)


# Broken out into its own table due to MySQL (5.0/1.x, anyway) not allowing NULL values in geometry columns.
class RideTrack(db.Model):
    __tablename__ = 'ride_tracks'
    __table_args__ = {'mysql_engine': 'MyISAM', 'mysql_charset': 'utf8'}  # MyISAM for spatial indexes

    ride_id = sa.Column(sa.BigInteger, sa.ForeignKey('rides.id'), primary_key=True)
    gps_track = ga.GeometryColumn(ga.LineString(2), nullable=False)
    elevation_stream = sa.Column(JSONEncodedText, nullable=True)
    time_stream = sa.Column(JSONEncodedText, nullable=True)

    def __repr__(self):
        return '<{0} ride_id={1}>'.format(self.__class__.__name__,  self.ride_id)

class RideEffort(db.Model):
    __tablename__ = 'ride_efforts'
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=False)
    ride_id = sa.Column(sa.BigInteger, sa.ForeignKey('rides.id', ondelete="cascade"), index=True)
    segment_name = sa.Column(sa.String(255), nullable=False)
    segment_id = sa.Column(sa.BigInteger, nullable=False, index=True)
    elapsed_time = sa.Column(sa.Integer, nullable=False)

    def __repr__(self):
        return '<{} id={} segment_name={!r}>'.format(self.__class__.__name__, self.id, self.segment_name)


class RidePhoto(db.Model):
    __tablename__ = 'ride_photos'

    id = sa.Column(sa.String(191), primary_key=True, autoincrement=False)
    source = sa.Column(sa.Integer, nullable=False, default=2)
    ride_id = sa.Column(sa.BigInteger, sa.ForeignKey('rides.id', ondelete="cascade"), index=True)
    ref = sa.Column(sa.String(255), nullable=False)
    caption = sa.Column(sa.Text, nullable=True)

    img_t = sa.Column(sa.String(255), nullable=True)
    img_l = sa.Column(sa.String(255), nullable=True)

    @property
    def img_l_dimensions(self):
        (width, height) = (None, None)
        if self.img_l:
            if self.source == 1:
                try:
                    (width, height) = re.match('.+-(\d+)x(\d+)\.\w+$', self.img_l).groups()
                except AttributeError:
                    warnings.warn("Unable to get width and height from source=1 image url: {}".format(self.img_l))
            else:
                (width, height) = (612,612)
        return (width, height)

    primary = sa.Column(sa.Boolean, nullable=False, default=False)

    # upload_date = sa.Column(sa.DateTime, nullable=False, index=True) # 2010-02-28T08:31:35Z

    def __repr__(self):
        return '<{} id={} primary={!r}>'.format(self.__class__.__name__, self.id, self.primary)


class RideWeather(db.Model):
    __tablename__ = 'ride_weather'
    ride_id = sa.Column(sa.BigInteger, sa.ForeignKey('rides.id'), primary_key=True)

    ride_temp_start = sa.Column(sa.Float, nullable=True)
    ride_temp_end = sa.Column(sa.Float, nullable=True)
    ride_temp_avg = sa.Column(sa.Float, nullable=True)

    ride_windchill_start = sa.Column(sa.Float, nullable=True)
    ride_windchill_end = sa.Column(sa.Float, nullable=True)
    ride_windchill_avg = sa.Column(sa.Float, nullable=True)

    ride_precip = sa.Column(sa.Float, nullable=True)  # In inches
    ride_rain = sa.Column(sa.Boolean, default=False, nullable=False)
    ride_snow = sa.Column(sa.Boolean, default=False, nullable=False)

    day_temp_min = sa.Column(sa.Float, nullable=True)
    day_temp_max = sa.Column(sa.Float, nullable=True)

    sunrise = sa.Column(sa.Time, nullable=True)
    sunset = sa.Column(sa.Time, nullable=True)

    def __repr__(self):
        return '<{0} ride_id={1}>'.format(self.__class__.__name__, self.id, self.segment_name)


# Setup Geometry columns
ga.GeometryDDL(RideGeo.__table__)
ga.GeometryDDL(RideTrack.__table__)


# Setup a Pool event to get MySQL to use strict SQL mode ...
# (This is the default now in 5.7+, so not necessary.)
def _set_sql_mode(dbapi_con, connection_record):
    # dbapi_con.cursor().execute("SET sql_mode = 'STRICT_TRANS_TABLES';")
    pass


sa.event.listen(Pool, 'connect', _set_sql_mode)

# Create VIEWS that may be helpful.

_v_daily_scores_create = sa.DDL("""
    drop view if exists daily_scores;
    create view daily_scores as
    select A.team_id, R.athlete_id, sum(R.distance) as distance,
    (sum(R.distance) + IF(sum(R.distance) >= 1.0, 10,0)) as points,
    date(R.start_date) as ride_date
    from rides R
    join athletes A on A.id = R.athlete_id
    group by R.athlete_id, A.team_id, date(R.start_date)
    ;
""")

sa.event.listen(Ride.__table__, 'after_create', _v_daily_scores_create)

_v_buid_ride_daylight = sa.DDL("""
    create view _build_ride_daylight as
    select R.id as ride_id, date(R.start_date) as ride_date,
    sec_to_time(R.elapsed_time) as elapsed,
    sec_to_time(R.moving_time) as moving,
    TIME(R.start_date) as start_time,
    TIME(date_add(R.start_date, interval R.elapsed_time second)) as end_time,
    W.sunrise, W.sunset
    from rides R
    join ride_weather W on W.ride_id = R.id
    ;
    """)

# sa.event.listen(RideWeather.__table__, 'after_create', _v_buid_ride_daylight)

_v_ride_daylight = sa.DDL("""
    create view ride_daylight as
    select ride_id, ride_date, start_time, end_time, sunrise, sunset, moving,
    IF(start_time < sunrise, LEAST(TIMEDIFF(sunrise, start_time), moving), sec_to_time(0)) as before_sunrise,
    IF(end_time > sunset, LEAST(TIMEDIFF(end_time, sunset), moving), sec_to_time(0)) as after_sunset
    from _build_ride_daylight
    ;
    """)

_v_leaderboard_athletes = sa.DDL("""
    create view lbd_athletes as select a.id, a.name, a.display_name, a.team_id from athletes a
    join teams T on T.id=a.team_id where not T.leaderboard_exclude
    ;
    """)

# sa.event.listen(RideWeather.__table__, 'after_create', _v_ride_daylight)

def rebuild_views():
    # This import is kinda kludgy (and would be circular outside of this function) but our model engine is tied up with
    # the Flask framework (for now)
    from bafs import db
    sess = db.session  # @UndefinedVariable
    sess.execute(_v_daily_scores_create)
    sess.execute(sa.DDL("drop view if exists _build_ride_daylight;"))
    sess.execute(_v_buid_ride_daylight)
    sess.execute(sa.DDL("drop view if exists ride_daylight;"))
    sess.execute(_v_ride_daylight)
    sess.execute(sa.DDL("drop view if exists lbd_athletes;"))
    sess.execute(_v_leaderboard_athletes)
