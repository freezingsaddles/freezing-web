"""
Functions for interacting with the datastore and the strava apis.
"""
from __future__ import division
import functools
from collections import namedtuple

from dateutil import parser

from geoalchemy import WKTSpatialElement

#from strava.api.v1 import V1ServerProxy
#from strava.api.v2 import V2ServerProxy
#from strava import units
 
from stravalib import Client
from stravalib import model as strava_model
from stravalib import unithelper

from bafs.model import Athlete, Ride, RideGeo, RideEffort
from bafs import app, db, model

class StravaClientForAthlete(Client):
    """
    Creates a StravaClient for the specified athlete.
    """
    def __init__(self, athlete):
        if not isinstance(athlete, model.Athlete):
            athlete = db.session.get(model.Athlete, athlete) # @UndefinedVariable
        super(StravaClientForAthlete, self).__init__(access_token=athlete.access_token, rate_limit_requests=True)
    

# Just a wrapper so we're not too tightly coupled to flask logging
logger = lambda: app.logger

def register_athlete(strava_athlete, access_token):
    """
    Ensure specified athlete is added to database.
    """
    athlete = Athlete()
    athlete.id = strava_athlete.id
    athlete.name = '{0} {1}'.format(strava_athlete.firstname, strava_athlete.lastname).strip()
    athlete.access_token = access_token
    db.session.merge(athlete) # @UndefinedVariable
    db.session.commit() # @UndefinedVariable
    
def get_team_name(club_id):
    """
    Convenience function to return the club name, given the ID.
    """
    raise NotImplementedError()
    #client = V1ServerProxy()
    #return client.get_club(club_id)['name']
    
def list_rides(athlete_id, start_date=None, exclude_keywords=None):
    """
    List all of the rides for individual athlete.
    
    :param athlete_id: The numeric ID of the strava athlete.
    :type athlete_id: int
    
    :param start_date: The date to start listing rides. 
    :type start_date: :class:`datetime.date`
    
    :param exclude_keywords: A list of keywords to use for excluding rides from the results (e.g. "#NoBAFS")
    :type exclude_keywords: list
    
    :return: list of :class:`stravalib.model.Activity` objects for rides in reverse chronological order.
    :rtype: list
    """
    client = StravaClientForAthlete(athlete_id)
    
    if exclude_keywords is None:
        exclude_keywords = []
    
    def is_activity_excluded(activity):
        for keyword in exclude_keywords:
            if keyword.lower() in activity.name.lower():
                logger().info("Skipping ride {0} ({1}) due to presence of exlusion keyword: {2}".format(activity.id,
                                                                                                        activity.name,
                                                                                                        keyword))
                return True
        else:
            return False
        
    activities = client.get_activities(after=start_date, limit=None)
    filtered_rides = [a for a in activities if (a.type == strava_model.Activity.RIDE and not is_activity_excluded(a))]
    return filtered_rides

def write_ride(activity, team=None):
    """
    Takes the specified ride_id and merges together the V1 and V2 API data into model 
    objects and writes them to the database.
    
    :param activity: The Strava :class:`stravalib.model.Activity` object.
    :type activity: :class:`stravalib.model.Activity`
    
    :return: The written Ride model object.
    :rtype: :class:`bafs.model.Ride`
    """
    
    if activity.start_latlng:
        start_geo = WKTSpatialElement('POINT({lat} {lon})'.format(lat=activity.start_latlng.lat,
                                                                  lon=activity.start_latlng.lon)) 
    else:
        start_geo = None

    if activity.end_latlng:
        end_geo = WKTSpatialElement('POINT({lat} {lon})'.format(lat=activity.end_latlng.lat,
                                                                lon=activity.end_latlng.lon)) 
    else:
        end_geo = None
    
    athlete_id = activity.athlete.id
    
    # Find the model object for that athlete (or create if doesn't exist)
    athlete = db.session.query(Athlete).get(athlete_id)   # @UndefinedVariable
    if not athlete:
        # The athlete has to exist since otherwise we wouldn't be able to query their rides
        raise ValueError("Somehow you are attempting to write rides for an athlete not found in the database.")
        
    #db.session.merge(athlete) # @UndefinedVariable
    #db.session.commit() # @UndefinedVariable
    
    if start_geo is not None or end_geo is not None:
        ride_geo = RideGeo()
        ride_geo.start_geo = start_geo
        ride_geo.end_geo = end_geo
        ride_geo.ride_id = activity.id
        db.session.merge(ride_geo) # @UndefinedVariable
    
    try:
        location_parts = []
        if activity.location_city:
            location_parts.append(activity.location_city)
        if activity.location_state:
            location_parts.append(activity.location_state)
        location_str = ', '.join(location_parts)
        
        def td_to_seconds(td):
            # we ignore microseconds for this
            if not td:
                return None
            return td.seconds + td.days * 24 * 3600 
            
        ride = Ride(id=activity.id,
                    athlete=athlete,
                    name=activity.name,
                    start_date=activity.start_date_local,
                    distance=unithelper.miles(activity.distance),
                    average_speed=unithelper.mph(activity.average_speed),
                    maximum_speed=unithelper.mph(activity.max_speed),
                    elapsed_time=td_to_seconds(activity.elapsed_time),
                    moving_time=td_to_seconds(activity.moving_time),
                    location=location_str,
                    commute=activity.commute,
                    trainer=activity.trainer,
                    elevation_gain=unithelper.feet(activity.total_elevation_gain),
                    )
        
        db.session.merge(ride) # @UndefinedVariable
        
        logger().debug("Writing ride: {athlete!r}: \"{ride!r}\" on {date}".format(athlete=athlete.name,
                                                                            ride=ride.name,
                                                                            date=ride.start_date.strftime('%m/%d/%y')))
        db.session.commit() # @UndefinedVariable
    except:
        logger().exception("Error adding ride: {0}".format(activity))
        raise
    
    return ride


def write_ride_efforts(ride):
    """
    Writes out all effort associated with a ride to the database.
    
    :param ride: The :class:`stravalib.model.Activity` that is associated with this effort.
    :type ride: :class:`stravalib.model.Activity`
    """
    try:
        for se in ride.segment_efforts:
            effort = RideEffort(id=se.id,
                                ride_id=ride.id,
                                elapsed_time=se.elapsed_time,
                                segment_name=se.segment.name,
                                segment_id=se.segment.id)
             
            db.session.merge(effort) # @UndefinedVariable
             
         
            logger().debug("Writing ride effort: {ride_id!r}: \"{effort!r}\"".format(ride_id=ride.id,
                                                                                     effort=effort.segment_name))
         
        ride.efforts_fetched = True
        db.session.commit() # @UndefinedVariable
    except:
        logger().exception("Error adding effort for ride: {0}".format(ride))
        raise
#     
