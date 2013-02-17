"""
Functions for interacting with the datastore and the strava apis.
"""
import functools
from collections import namedtuple

from dateutil import parser

from geoalchemy import WKTSpatialElement

from strava.api.v1 import V1ServerProxy
from strava.api.v2 import V2ServerProxy
from strava import units
 
from bafs.model import Athlete, Ride, RideGeo
from bafs import app, db


RideIndexEntry = namedtuple('RideIndexEntry', ['id', 'name'])

# Just a wrapper so we're not too tightly coupled to flask logging
logger = lambda: app.logger

def get_team_name(club_id):
    """
    Convenience function to return the club name, given the ID.
    """
    v1api = V1ServerProxy()
    return v1api.get_club(club_id)['name']
    
def list_rides(athlete_id=None, club_id=None, start_date=None, exclude_keywords=None):
    """
    List all of the rides for specified team club or individual athlete.
    
    :param athlete_id: The numeric ID of the strava athlete.
    :type athlete_id: int
    :param club_id: The numeric identifier of the strava club.
    :type club_id: int
    :param start_date: The date to start listing rides. 
    :type start_date: :class:`datetime.date`
    :param exclude_keywords: A list of keywords to use for excluding rides from the results (e.g. "#NoBAFS")
    :type exclude_keywords: list
    :return: list of (id, name) tuple for rides in club in reverse chronological order.
    :rtype: list
    """
    v1api = V1ServerProxy()
    
    if athlete_id and club_id:
        raise ValueError("Cannot specify both athlete_id and club_id")
    elif not athlete_id and not club_id:
        raise ValueError("Either athlete_id or club_id is required")
    
    if exclude_keywords is None:
        exclude_keywords = []
    
    kw = {}
    if start_date:
        kw['startDate'] = start_date
    if athlete_id:
        kw['athleteId'] = athlete_id
    if club_id:
        kw['clubId'] = club_id
        
    apifunc = functools.partial(v1api.list_rides, **kw)
    
    # By default only 50 rows are returned so we have to itereate over until we get to the end. 
    all_rides = []
    offset = 0
    while True:
        logger().debug("Fetching rides {0} - {1}".format(offset, offset + 50))
        rides = apifunc(clubId=club_id, offset=offset)
        logger().debug("Fetched {0} rides".format(len(rides)))
        
        # This would be a nice list comprehension, but we break it out for purposes of logging 
        for ride in rides:
            for keyword in exclude_keywords:
                if keyword.lower() in ride['name'].lower():
                    logger().info("Skipping ride {0} ({1}) due to presence of exlusion keyword: {2}".format(ride['id'], ride['name'], keyword))
                    break
            else:
                # If we need not break of out the loop then it means no keywords matched, so append it.
                # (This also covers the case where no exclusion keywords were specified.)
                all_rides.append(RideIndexEntry(id=ride['id'], name=ride['name']))
            
        if len(rides) < 50:
            break
        offset += 50
        
    return all_rides

def write_ride(ride_id, team=None):
    """
    Takes the specified ride_id and merges together the V1 and V2 API data into model 
    objects and writes them to the database.

    :param ride_id: The ride that should be filled in and written to DB.
    :type ride_id: int
    
    :param team: The affiliated team club entity (or none for detached riders).
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
    
    if start_geo is not None and end_geo is not None:
        ride_geo = RideGeo()
        ride_geo.start_geo = start_geo
        ride_geo.end_geo = end_geo
    else:
        ride_geo = None
    
    try:    
        ride = Ride(id=v2data['id'],
                    athlete=athlete,
                    name=v2data['name'],
                    start_date=parser.parse(v2data['start_date_local']),
                    distance=units.meters_to_miles(v2data['distance']),
                    average_speed=units.metersps_to_mph(v1data['averageSpeed']),
                    maximum_speed=units.kph_to_mph(v1data['maximumSpeed'] / 1000.0), # Not sure why this is in meters per hour ... !?
                    elapsed_time=v2data['elapsed_time'],
                    moving_time=v2data['moving_time'],
                    location=v2data.get('location'),
                    commute=v1data['commute'],
                    trainer=v1data['trainer'],
                    geo=ride_geo,
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