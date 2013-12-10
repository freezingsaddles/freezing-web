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

from bafs.model import Athlete, Ride, RideGeo, RideEffort, Team
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
    Ensure specified athlete is added to database, returns athlete model.
    
    :return: The added athlete model object.
    :rtype: :class:`bafs.model.Athlete`
    """
    athlete = Athlete()
    athlete.id = strava_athlete.id
    athlete.name = '{0} {1}'.format(strava_athlete.firstname, strava_athlete.lastname).strip()
    athlete.access_token = access_token
    db.session.merge(athlete) # @UndefinedVariable
    db.session.commit() # @UndefinedVariable
    return athlete

class MultipleTeamsError(RuntimeError):
    def __init__(self, teams):
        self.teams = teams

class NoTeamsError(RuntimeError):
    pass

def register_athlete_team(strava_athlete, athlete_model):
    """
    Updates db with configured team that matches the athlete's teams.
    
    Updates the passed-in Athlete model object with created/updated team.
    
    :param strava_athlete: The Strava model object for the athlete.
    :type strava_athlete: :class:`stravalib.model.Athlete`
    
    :param athlete_model: The athlete model object.
    :type athlete_model: :class:`bafs.model.Athlete`
    
    :return: The :class:`bafs.model.Team` object will be returned which matches 
             configured teams.
    :rtype: :class:`bafs.model.Team`
    
    :raise MultipleTeamsError: If this athlete is registered for multiple of
                               the configured teams.  That won't work.
    :raise NoTeamsError: If no teams match. 
    """
    assert isinstance(strava_athlete, strava_model.Athlete)
    assert isinstance(athlete_model, Athlete)
    
    logger().info("Checking {0!r} against {1!r}".format(strava_athlete.clubs, app.config['BAFS_TEAMS']))
    matches = [c for c in strava_athlete.clubs if c.id in app.config['BAFS_TEAMS']]
    if len(matches) > 1:
        raise MultipleTeamsError(matches)
    elif len(matches) == 0:
        raise NoTeamsError()
    else:
        club = matches[0]
        # create the team row
        team = Team()
        team.id = club.id
        team.name = club.name
        athlete_model.team = team
        db.session.merge(team) # @UndefinedVariable
        db.session.commit() # @UndefinedVariable
        return team
    
def get_team_name(club_id):
    """
    Convenience function to return the club name, given the ID.
    """
    raise NotImplementedError()
    #client = V1ServerProxy()
    #return client.get_club(club_id)['name']
    
def list_rides(athlete, start_date=None, exclude_keywords=None):
    """
    List all of the rides for individual athlete.
    
    :param athlete: The Athlete model object.
    :type athlete: :class:`bafs.model.Athlete`
    
    :param start_date: The date to start listing rides. 
    :type start_date: :class:`datetime.date`
    
    :param exclude_keywords: A list of keywords to use for excluding rides from the results (e.g. "#NoBAFS")
    :type exclude_keywords: list
    
    :return: list of :class:`stravalib.model.Activity` objects for rides in reverse chronological order.
    :rtype: list
    """
    client = StravaClientForAthlete(athlete)
    
    if exclude_keywords is None:
        exclude_keywords = []
    
    def is_keyword_excluded(activity):
        for keyword in exclude_keywords:
            if keyword.lower() in activity.name.lower():
                logger().info("Skipping ride {0} ({1}) due to presence of exlusion keyword: {2}".format(activity.id,
                                                                                                        activity.name,
                                                                                                        keyword))
                return True
        else:
            return False
        
    activities = client.get_activities(after=start_date, limit=None)
    filtered_rides = [a for a in activities if (a.type == strava_model.Activity.RIDE and not a.trainer and not is_keyword_excluded(a))]
    return filtered_rides

def timedelta_to_seconds(td):
    """
    Converts a timedelta to total seconds.
    (This is built-in in Python 2.7)
    """
    # we ignore microseconds for this
    if not td:
        return None
    return td.seconds + td.days * 24 * 3600

def write_ride(activity):
    """
    Takes the specified activity and writes it to the database.
    
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
        
        logger().debug("Got distance: {0!r}".format(activity.distance))
        
        ride = Ride(id=activity.id,
                    athlete=athlete,
                    name=activity.name,
                    start_date=activity.start_date_local,
                    distance=float(unithelper.miles(activity.distance)),
                    average_speed=float(unithelper.mph(activity.average_speed)),
                    maximum_speed=float(unithelper.mph(activity.max_speed)),
                    elapsed_time=timedelta_to_seconds(activity.elapsed_time),
                    moving_time=timedelta_to_seconds(activity.moving_time),
                    location=location_str,
                    commute=activity.commute,
                    trainer=activity.trainer,
                    elevation_gain=float(unithelper.feet(activity.total_elevation_gain)),
                    )
        
        logger().debug("Writing ride for {athlete!r}: \"{ride!r}\" on {date}".format(athlete=athlete.name,
                                                                                     ride=ride.name,
                                                                                     date=ride.start_date.strftime('%m/%d/%y')))
        
        # db.session.merge() is *not* happy here.  (Duplicates get added for some weird reason.)
        db.session.add(ride) # @UndefinedVariable
        db.session.commit() # @UndefinedVariable
    except:
        logger().exception("Error adding ride: {0}".format(activity))
        raise
    
    return ride


def write_ride_efforts(strava_activity, ride):
    """
    Writes out all effort associated with a ride to the database.
    
    :param strava_activity: The :class:`stravalib.model.Activity` that is associated with this effort.
    :type strava_activity: :class:`stravalib.model.Activity`
    
    :param ride: The db model object for ride.
    :type ride: :class:`bafs.model.Ride`
    """
    assert isinstance(strava_activity, strava_model.Activity)
    assert isinstance(ride, Ride)
    
    try:
        for se in strava_activity.segment_efforts:
            effort = RideEffort(id=se.id,
                                ride_id=strava_activity.id,
                                elapsed_time=timedelta_to_seconds(se.elapsed_time),
                                segment_name=se.segment.name,
                                segment_id=se.segment.id)
            
            logger().debug("Writing ride effort: {se_id}: {effort!r}".format(se_id=se.id,
                                                                             effort=effort.segment_name))
          
            db.session.merge(effort) # @UndefinedVariable
             
        ride.efforts_fetched = True
        db.session.commit() # @UndefinedVariable
    except:
        logger().exception("Error adding effort for ride: {0}".format(ride))
        raise
#     
