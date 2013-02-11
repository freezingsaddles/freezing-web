import abc

from bafs import db

import sqlalchemy as sa
import geoalchemy as ga
from sqlalchemy import orm

class StravaEntity(db.Model):
    __metaclass__ = abc.ABCMeta
    
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(1024))
    
    def __init__(self, id=None, name=None, **kwargs):
        self.id = id
        self.name = name
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        
    def __repr__(self):
        return '<{} id={} name={}>'.format(self.__class__.__name__, self.id, self.name)

class Team(StravaEntity):    
    """
    """
    athletes = orm.relationship("Athlete", backref="team")
    
class Athlete(StravaEntity):    
    """
    """
    rides = orm.relationship("Ride", backref="athlete", lazy="dynamic")
    
class Ride(StravaEntity):    
    """
    """
    elapsed_time = sa.Column(sa.Integer) # Seconds
    # in case we want to conver that to a TIME type ... (using time for interval is kinda mysql-specific brokenness, though)
    # time.strftime('%H:%M:%S', time.gmtime(12345))
    moving_time = sa.Column(sa.Integer) # 
    elevation_gain = sa.Column(sa.Integer) # 269.6 (feet)
    average_speed = sa.Column(sa.Float) # mph
    maximum_speed = sa.Column(sa.Float) # mph
    start_date = sa.Column(sa.DateTime) # 2010-02-28T08:31:35Z
    distance = sa.Column(sa.Float) # 82369.1 (meters)
    location = sa.Column(sa.String(255))
    start_geo = ga.GeometryColumn(ga.Point(2))
    end_geo = ga.GeometryColumn(ga.Point(2))
    commute = sa.Column(sa.Boolean)
    trainer = sa.Column(sa.Boolean)

ga.GeometryDDL(Ride.__table__)