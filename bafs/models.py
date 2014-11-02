'''
Created on Oct 26, 2014

@author: hans
'''
from django.contrib.gis.db import models

class StravaEntity(models.Model):
    class Meta:
        abstract = True
        
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=1024)
    
    def __unicode__(self):
        return u'{} ({})'.format(self.name, self.id)
    
    def __repr__(self):
        return '<{0} id={1} name={2!r}>'.format(self.__class__.__name__, self.id, self.name)

class Team(StravaEntity):    
    """
    """
    class Meta:
        db_table = 'teams'
    
class Athlete(StravaEntity):    
    """
    """
    class Meta:
        db_table = 'athletes'
        
    display_name = models.CharField(max_length=255, null=True)
    team = models.ForeignKey(Team, null=True, on_delete=models.SET_NULL) # XXX: BigInteger
    access_token = models.CharField(max_length=255, null=True)
    # TODO:
    #rides = orm.relationship("Ride", backref="athlete", lazy="dynamic", cascade="all, delete, delete-orphan")
    
class Ride(StravaEntity):    
    """
    """
    class Meta:
        db_table = 'rides'
    
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE)
    elapsed_time = models.IntegerField() # Seconds
    # in case we want to conver that to a TIME type ... (using time for interval is kinda mysql-specific brokenness, though)
    # time.strftime('%H:%M:%S', time.gmtime(12345))
    moving_time = models.IntegerField(db_index=True) # 
    elevation_gain = models.IntegerField(null=True) # 269.6 (feet)
    average_speed = models.FloatField(null=True) # mph
    maximum_speed = models.FloatField(null=True) # mph
    start_date = models.DateTimeField(db_index=True) # 2010-02-28T08:31:35Z
    distance = models.FloatField(db_index=True) # 82369.1 (meters)
    location = models.CharField(max_length=255, null=True)
    
    commute = models.NullBooleanField()
    trainer = models.NullBooleanField()
    
    efforts_fetched = models.BooleanField(default=False, null=False)
    
    timezone = models.CharField(max_length=255, null=True)
    
    manual = models.NullBooleanField()
    
    #geo = orm.relationship("RideGeo", uselist=False, backref="ride", cascade="all, delete, delete-orphan")
    #weather = orm.relationship("RideWeather", uselist=False, backref="ride", cascade="all, delete, delete-orphan")
    

# Broken out into its own table due to MySQL (5.0/1.x, anyway) not allowing NULL values in geometry columns.
class RideGeo(models.Model):
    class Meta:
        db_table = 'ride_geo'
        #__table_args__ = {'mysql_engine':'MyISAM'} # MyISAM for spatial indexes
        
    ride = models.ForeignKey(Ride, primary_key=True)
    start_geo = models.PointField(null=True)
    end_geo = models.PointField(null=True)

    # GeoDjango-specific:
    # overriding the default manager with a GeoManager instance.
    objects = models.GeoManager()
    
    def __repr__(self):
        return '<{0} ride_id={1} start={2}>'.format(self.__class__.__name__,
                                                          self.ride_id,
                                                          self.start_geo)

class RideEffort(models.Model):
    class Meta:
        db_table = 'ride_efforts'
        
    id = models.BigIntegerField(primary_key=True)
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE)
    segment_name = models.CharField(max_length=255, null=False)
    segment_id = models.BigIntegerField(null=False, db_index=True)
    elapsed_time = models.IntegerField(null=False)

    def __repr__(self):
        return '<{0} id={1} segment_name={1!r}>'.format(self.__class__.__name__, self.id, self.segment_name)

class RideWeather(models.Model):
    class Meta:
        db_table = 'ride_weather'
        
    ride = models.ForeignKey(Ride, primary_key=True)
    
    ride_temp_start = models.FloatField(null=True)
    ride_temp_end = models.FloatField(null=True)
    ride_temp_avg = models.FloatField(null=True)
    
    ride_windchill_start = models.FloatField(null=True)
    ride_windchill_end = models.FloatField(null=True)
    ride_windchill_avg = models.FloatField(null=True)
    
    ride_precip = models.FloatField(null=True) # In inches
    ride_rain = models.BooleanField(default=False, null=False)
    ride_snow = models.BooleanField(default=False, null=False)
    
    day_temp_min = models.FloatField(null=True)
    day_temp_max = models.FloatField(null=True)
    
    sunrise = models.TimeField(null=True)
    sunset = models.TimeField(null=True)
    
    def __repr__(self):
        return '<{0} ride_id={1}>'.format(self.__class__.__name__, self.id, self.segment_name)