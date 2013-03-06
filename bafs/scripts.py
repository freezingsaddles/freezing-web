import optparse
import logging
import re
import time
from datetime import datetime, timedelta
from pprint import pprint

from dateutil import parser as dateutil_parser
from sqlalchemy import not_, and_, text
from pytz import timezone

from bafs import app, db
from bafs import data, model
from weather.wunder import api as wu_api
from weather.wunder import model as wu_model
from weather.sunrise import Sun

def init_db():
    """
    Initialize the database.
    """
    logging.basicConfig(level=logging.INFO)
    parser = optparse.OptionParser()
    
    parser.add_option("--drop", action="store_true", dest="drop", default=False, 
                      help="Whether to drop tables.")
    
    (options, args) = parser.parse_args()
    
    if options.drop:
        app.logger.info("Dropping tables.")
        db.drop_all()
    db.create_all()
    
    model.rebuild_views()

    
def sync_rides():
    """
    Synchronize rides from strava with the database.
    """
    parser = optparse.OptionParser()
    
    parser.add_option("--start-date", dest="start_date",
                      help="Date to begin fetching (default is to fetch all since configured start date)",
                      default=app.config['BAFS_START_DATE'],
                      metavar="YYYY-MM-DD")
    
    parser.add_option("--clear", action="store_true", dest="clear", default=False, 
                      help="Whether to clear data before fetching.")
    
    parser.add_option("--debug", action="store_true", dest="debug", default=False, 
                      help="Whether to log at debug level.")
    
    parser.add_option("--quiet", action="store_true", dest="quiet", default=False, 
                      help="Whether to suppress non-error log output.")
    
    (options, args) = parser.parse_args()
    
    if options.quiet:
        loglevel = logging.ERROR
    elif options.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
        
    logging.basicConfig(level=loglevel)
    logger = logging.getLogger('sync')
    
    sess = db.session
    
    if options.start_date:
        start = dateutil_parser.parse(options.start_date)
        logger.info("Fetching rides newer than {0}".format(start))
    else:
        start=None
        logger.info("Fetching all rides")
    
    if options.clear:
        #logger.info("Clearing all data!")
        #sess.query(model.RideGeo).delete()
        #sess.query(model.Ride).delete()
        #sess.query(model.Athlete).delete()
        #sess.query(model.Team).delete()
        logger.info("Clear is currently not enabled due to the amount of time to reconstruct from scratch.")
        
    for club_id in app.config['BAFS_TEAMS']:
        team = model.Team(id=club_id,
                          name=data.get_team_name(club_id))
        sess.merge(team)
        sess.commit()
        
        logger.info("Fetching rides for team: {name!r} ({id})".format(name=team.name, id=team.id))
        _write_rides(start, team=team)
        
    for athlete_id in app.config['BAFS_FREE_RIDERS']:
        logger.info("Fetching rides for athlete: {0}".format(athlete_id))
        _write_rides(start, athlete_id=athlete_id)

def _write_rides(start, team=None, athlete_id=None, rewrite=False):
    
    logger = logging.getLogger('sync')
    
    if team and athlete_id:
        raise ValueError("team and athlete params are mutually exclusive")
    elif team is None and athlete_id is None:
        raise ValueError("either team or athlete_id param is required")
    
    sess = db.session
    
    if team:
        api_ride_entries = data.list_rides(club_id=team.id, start_date=start, exclude_keywords=app.config.get('BAFS_EXCLUDE_KEYWORDS'))
        q = sess.query(model.Ride)
        q = q.filter(and_(model.Ride.athlete_id.in_(sess.query(model.Athlete.id).filter(model.Athlete.team_id==team.id)),
                          model.Ride.start_date >= start))
        db_rides = q.all()
    else:
        api_ride_entries = data.list_rides(athlete_id=athlete_id, start_date=start, exclude_keywords=app.config.get('BAFS_EXCLUDE_KEYWORDS'))
        q = sess.query(model.Ride)
        q = q.filter(and_(model.Ride.athlete_id == athlete_id,
                          model.Ride.start_date >= start))
        db_rides = q.all()
    
    # Quickly filter out only the rides that are not in the database.
    returned_ride_ids = set([r.id for r in api_ride_entries])
    stored_ride_ids = set([r.id for r in db_rides])
    new_ride_ids = list(returned_ride_ids - stored_ride_ids)
    removed_ride_ids = list(stored_ride_ids - returned_ride_ids)
    num_rides = len(new_ride_ids)
    
    for (i, ri_entry) in enumerate([r_i for r_i in api_ride_entries if r_i.id in new_ride_ids]):
        logger.info("Processing ride: {0} ({1}/{2})".format(ri_entry.id, i, num_rides))
        if rewrite or not ri_entry.id in stored_ride_ids:
            ride = data.write_ride(ri_entry.id, team=team)
            logger.debug("Wrote new ride: %r" % (ride,))
        else:
            logger.debug("Skipping existing ride: {id} - {name!r}".format(name=ri_entry.name,id=ri_entry.id))

    # Remove any rides that are in the database for this team that were not in the returned list.
    if removed_ride_ids:
        q = sess.query(model.Ride)
        q = q.filter(model.Ride.id.in_(removed_ride_ids))
        deleted = q.delete(synchronize_session=False)
        if team:
            logger.info("Removed {0} no longer present rides for team {1}.".format(deleted, team.id))
        else:
            logger.info("Removed {0} no longer present rides for athlete {1}.".format(deleted, athlete_id))
    else:
        if team:
            logger.info("(No removed rides for team {0!r}.)".format(team))
        else:
            logger.info("(No removed rides for athlete {0}.)".format(athlete_id))
    
    
    sess.commit() 
        
    # Write out any efforts associated with these rides (not already in database)
    q = sess.query(model.Ride).filter_by(efforts_fetched=False)
    for ride in q.all():
        logger.info("Writing out efforts for {0!r}".format(ride))
        data.write_ride_efforts(ride)
        
def sync_ride_weather():
    """
    Synchronize rides from strava with the database.
    """
    parser = optparse.OptionParser()
    
    parser.add_option("--clear", action="store_true", dest="clear", default=False, 
                      help="Whether to clear data before fetching.")
    
    parser.add_option("--cache-only", action="store_true", dest="cache_only", default=False, 
                      help="Whether to only use existing cache.")
    
    parser.add_option("--limit", type="int", dest="limit", default=0, 
                      help="Limit how many rides are processed (e.g. during development)")
    
    parser.add_option("--debug", action="store_true", dest="debug", default=False, 
                      help="Whether to log at debug level.")
    
    parser.add_option("--quiet", action="store_true", dest="quiet", default=False, 
                      help="Whether to suppress non-error log output.")
    
    (options, args) = parser.parse_args()
    
    if options.quiet:
        loglevel = logging.ERROR
    elif options.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
        
    logging.basicConfig(level=loglevel)
    logger = logging.getLogger('sync')
    
    sess = db.session
    
    if options.clear:
        logger.info("Clearing all weather data!")
        sess.query(model.RideWeather).delete()
    
    if options.limit:
        logger.info("Fetching weather for first {0} rides".format(options.limit))
    else:
        logger.info("Fetching weather for all rides")
    
    # Find rides that have geo, but no weather 
    sess.query(model.RideWeather)
    q = text("""
        select R.id from rides R
        join ride_geo G on G.ride_id = R.id
        left join ride_weather W on W.ride_id = R.id
        where W.ride_id is null;
        """)
    
    c = wu_api.Client(api_key=app.config['WUNDERGROUND_API_KEY'],
                      cache_dir=app.config['WUNDERGROUND_CACHE_DIR'],
                      pause=7.0, # Max requests 10/minute for developer license
                      cache_only=options.cache_only)
    
    rx = re.compile('^POINT\((.+)\)$')
    
    rows = db.engine.execute(q).fetchall() # @UndefinedVariable
    num_rides = len(rows)

    for i,r in enumerate(rows):
    
        if options.limit and i > options.limit:
            logging.info("Limit ({0}) reached".format(options.limit))
            break
        
        ride =  db.session.query(model.Ride).get(r['id']) # @UndefinedVariable
        logger.info("Processing ride: {0} ({1}/{2})".format(ride.id, i, num_rides))
        
        try:
            
            start_geo_wkt = db.session.scalar(ride.geo.start_geo.wkt) # @UndefinedVariable
            
            (lat,lon) = rx.match(start_geo_wkt).group(1).split(' ')
            hist = c.history(ride.start_date, us_city=ride.location, lat=lat, lon=lon)
                        
            ride_start = ride.start_date.replace(tzinfo=hist.date.tzinfo)
            ride_end = ride_start + timedelta(seconds=ride.elapsed_time)
            
            # NOTE: if elapsed_time is significantly more than moving_time then we need to assume
            # that the rider wasn't actually riding for this entire time (and maybe just grab temps closest to start of
            # ride as opposed to averaging observations during ride.
            
            ride_observations = hist.find_observations_within(ride_start, ride_end)
            start_obs = hist.find_nearest_observation(ride_start)
            end_obs = hist.find_nearest_observation(ride_end)
            
            def avg(l):
                no_nulls = [e for e in l if e is not None]
                if not no_nulls:
                    return None
                return sum(no_nulls) / len(no_nulls) * 1.0 # to force float
            
            rw = model.RideWeather()
            rw.ride_id = ride.id
            rw.ride_temp_start = start_obs.temp
            rw.ride_temp_end = end_obs.temp
            if len(ride_observations) <= 2:
                # bookend the observations with the start/end observations
                ride_observations = [start_obs] + ride_observations + [end_obs]
                
            rw.ride_temp_avg = avg([o.temp for o in ride_observations])  
            
            rw.ride_windchill_start = start_obs.windchill
            rw.ride_windchill_end = end_obs.windchill
            rw.ride_windchill_avg = avg([o.windchill for o in ride_observations])
            
            rw.ride_precip = sum([o.precip for o in ride_observations if o.precip is not None])
            rw.ride_rain = any([o.rain for o in ride_observations])
            rw.ride_snow = any([o.snow for o in ride_observations])
            
            rw.day_temp_min = hist.min_temp
            rw.day_temp_max = hist.max_temp
            
            ride.weather_fetched = True
            ride.timezone = hist.date.tzinfo.zone 
            
            sess.add(rw)
            sess.flush()
        
            if lat and lon:
                try:
                    sun = Sun(lat=lat, lon=lon)
                    rw.sunrise = sun.sunrise(ride_start)
                    rw.sunset = sun.sunset(ride_start)
                except:
                    logger.exception("Error getting sunrise/sunset for ride {0}".format(ride))
                    # But don't throw away everything.
        except:
            logger.exception("Error getting weather data for ride: {0}".format(ride))
            # But continue on.
            
    sess.commit() 