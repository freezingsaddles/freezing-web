import abc

from bafs import db

import sqlalchemy as sa
import geoalchemy as ga
from sqlalchemy import orm
from sqlalchemy.pool import Pool


from sqlalchemy import Table
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Executable, ClauseElement

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
    __table_args__ = {'mysql_engine':'InnoDB'} # But we use MyISAM for the spatial table.
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=False)
    name = sa.Column(sa.String(1024), nullable=False)
    
    def __init__(self, id=None, name=None, **kwargs):
        self.id = id
        self.name = name
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        
    def __repr__(self):
        return '<{0} id={1} name={1!r}>'.format(self.__class__.__name__, self.id, self.name)

class Team(StravaEntity):    
    """
    """
    __tablename__ = 'teams'
    athletes = orm.relationship("Athlete", backref="team")
    
class Athlete(StravaEntity):    
    """
    """
    __tablename__ = 'athletes'
    team_id = sa.Column(sa.Integer, sa.ForeignKey('teams.id', ondelete='set null'))
    rides = orm.relationship("Ride", backref="athlete", lazy="dynamic", cascade="all, delete, delete-orphan")
    
class Ride(StravaEntity):    
    """
    """
    __tablename__ = 'rides'
    athlete_id = sa.Column(sa.Integer, sa.ForeignKey('athletes.id', ondelete='cascade'), nullable=False)
    elapsed_time = sa.Column(sa.Integer, nullable=False) # Seconds
    # in case we want to conver that to a TIME type ... (using time for interval is kinda mysql-specific brokenness, though)
    # time.strftime('%H:%M:%S', time.gmtime(12345))
    moving_time = sa.Column(sa.Integer, nullable=False) # 
    elevation_gain = sa.Column(sa.Integer, nullable=True) # 269.6 (feet)
    average_speed = sa.Column(sa.Float) # mph
    maximum_speed = sa.Column(sa.Float) # mph
    start_date = sa.Column(sa.DateTime, nullable=False) # 2010-02-28T08:31:35Z
    distance = sa.Column(sa.Float, nullable=False) # 82369.1 (meters)
    location = sa.Column(sa.String(255), nullable=True)
    
    commute = sa.Column(sa.Boolean, nullable=True)
    trainer = sa.Column(sa.Boolean, nullable=True)
    
    geo = orm.relationship("RideGeo", uselist=False, backref="ride", cascade="all, delete, delete-orphan")

# Broken out into its own table due to MySQL (5.0/1.x, anyway) not allowing NULL values in geometry columns.
class RideGeo(db.Model):
    __tablename__ = 'ride_geo'
    __table_args__ = {'mysql_engine':'MyISAM'} # MyISAM for spatial indexes
    
    ride_id = sa.Column(sa.Integer, sa.ForeignKey('rides.id'), primary_key=True)
    start_geo = ga.GeometryColumn(ga.Point(2))
    end_geo = ga.GeometryColumn(ga.Point(2))

    def __repr__(self):
        return '<{0} ride_id={1} start={2}>'.format(self.__class__.__name__,
                                                          self.ride_id,
                                                          self.start_geo)

class RideEffort(db.Model):
    __tablename__ = 'ride_efforts'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=False)
    ride_id = sa.Column(sa.Integer, sa.ForeignKey('rides.id', ondelete="cascade"), index=True)
    segment_name = sa.Column(sa.String(255), nullable=False)
    segment_id = sa.Column(sa.Integer, nullable=False)
    elapsed_time = sa.Column(sa.Integer, nullable=False)

    def __repr__(self):
        return '<{0} id={1} segment_name={1!r}>'.format(self.__class__.__name__, self.id, self.segment_name)


# Setup Geometry columns    
ga.GeometryDDL(Ride.__table__)

# Setup a Pool event to get MySQL to use strict SQL mode ...
def _set_sql_mode(dbapi_con, connection_record):
    dbapi_con.cursor().execute("SET sql_mode = 'STRICT_TRANS_TABLES';")

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


def rebuild_views():
    # This import is kinda kludgy (and would be circular outside of this function) but our model engine is tied up with
    # the Flask framework (for now)
    from bafs import db
    db.session.execute(_v_daily_scores_create) # 