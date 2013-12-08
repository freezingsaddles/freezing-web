"""
Functions for interacting with the datastore and the strava apis.
"""
import functools
from collections import namedtuple

from dateutil import parser

from geoalchemy import WKTSpatialElement

#from strava.api.v1 import V1ServerProxy
#from strava.api.v2 import V2ServerProxy
#from strava import units
 
from stravalib import Client
from stravalib import model as strava_model

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

def write_ride(ride_id, team=None):
    """
    Takes the specified ride_id and merges together the V1 and V2 API data into model 
    objects and writes them to the database.
    
    :param ride_id: The ride that should be filled in and written to DB.
    :type ride_id: int
    
    :param team: The team club entity.
    :type team: :class:`stravatools.bafs.model.Club`
    
    :return: The written Ride object.
    """
    v1sess = V1ServerProxy()
    v2sess = V2ServerProxy()
    
    v1data = v1sess.get_ride(ride_id)
    v2data = v2sess.get_ride(ride_id)
    
    #logger().info(repr(v2data))
    
    if v2data['start_latlng']:
        (lat,lon) = v2data['start_latlng']
        start_geo = WKTSpatialElement('POINT({lat} {lon})'.format(lat=lat, lon=lon)) 
    else:
        start_geo = None
        
    if v2data['end_latlng']:
        (lat,lon) = v2data['end_latlng'] 
        end_geo = WKTSpatialElement('POINT({lat} {lon})'.format(lat=lat, lon=lon))
    else:
        end_geo = None
    
    athlete_id = v1data['athlete']['id']
    
    # In the BAFS model, an athlete only belongs to a single team club (at most - there are a few unclubbed riders)
    athlete = Athlete(id=athlete_id,
                      team=team,
                      name=v1data['athlete']['name'])

    db.session.merge(athlete) # @UndefinedVariable
    db.session.commit() # @UndefinedVariable
    
    if start_geo is not None or end_geo is not None:
        ride_geo = RideGeo()
        ride_geo.start_geo = start_geo
        ride_geo.end_geo = end_geo
        ride_geo.ride_id = v2data['id']
        db.session.merge(ride_geo) # @UndefinedVariable
    
    try:    
        ride = Ride(id=v2data['id'],
                    athlete=athlete,
                    name=v2data['name'],
                    start_date=parser.parse(v2data['start_date_local']).replace(tzinfo=None),
                    distance=units.meters_to_miles(v2data['distance']),
                    average_speed=units.metersps_to_mph(v1data['averageSpeed']),
                    maximum_speed=units.kph_to_mph(v1data['maximumSpeed'] / 1000.0), # Not sure why this is in meters per hour ... !?
                    elapsed_time=v2data['elapsed_time'],
                    moving_time=v2data['moving_time'],
                    location=v2data.get('location'),
                    commute=v1data['commute'],
                    trainer=v1data['trainer'],
                    elevation_gain=units.meters_to_feet(v2data['elevation_gain']),
                    )
        
        db.session.merge(ride) # @UndefinedVariable
        
        logger().debug("Writing ride: {athlete!r}: \"{ride!r}\" on {date}".format(athlete=athlete.name,
                                                                            ride=ride.name,
                                                                            date=ride.start_date.strftime('%m/%d/%y')))
        db.session.commit() # @UndefinedVariable
    except:
        logger().exception("Error adding ride: {0}".format(ride_id))
        raise
    
    return ride


def write_ride_efforts(ride):
    """
    Writes out all effort associated with a ride to the database.
    
    :param ride: The :class:`stravalib.model.Activity` that is associated with this effort.
    :type ride: :class:`stravalib.model.Activity`
    """
    raise NotImplementedError()
#     v1sess = V1ServerProxy()
#     v1efforts = v1sess.get_ride_efforts(ride.id)
#     
#     try:
#         for v1data in v1efforts:
#             effort = RideEffort(id=v1data['id'],
#                                 ride_id=ride.id,
#                                 elapsed_time=v1data['elapsed_time'],
#                                 segment_name=v1data['segment']['name'],
#                                 segment_id=v1data['segment']['id'])
#             
#             db.session.merge(effort) # @UndefinedVariable
#             
#         
#             logger().debug("Writing ride effort: {ride_id!r}: \"{effort!r}\"".format(ride_id=ride.id,
#                                                                                      effort=effort.segment_name))
#         
#         ride.efforts_fetched = True
#         db.session.commit() # @UndefinedVariable
#     except:
#         logger().exception("Error adding effort for ride: {0}".format(ride.id))
#         raise
#     
