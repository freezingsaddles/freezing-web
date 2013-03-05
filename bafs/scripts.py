import optparse
import logging
import re
import time
from datetime import datetime
from dateutil import parser as dateutil_parser
from sqlalchemy import not_, and_, text

from bafs import app, db
from bafs import data, model
from wx.ncdc import api as ncdc_api
from wx.ncdc import model as ncdc_model
from wx.tzwhere import tzwhere
from wx.sunrise import Sun

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
        logger.info("Fetching weather for rides newer than {0}".format(start))
    else:
        start=None
        logger.info("Fetching weather for all rides")
    
    if options.clear:
        #logger.info("Clearing all data!")
        sess.query(model.RideWeather).delete()
        #sess.query(model.RideGeo).delete()
        #sess.query(model.Ride).delete()
        #sess.query(model.Athlete).delete()
        #sess.query(model.Team).delete()
        #logger.info("Clear is currently not enabled due to the amount of time to reconstruct from scratch.")
    
    
    # Find rides that have geo, but no weather 
    sess.query(model.RideWeather)
    q = text("""
        select R.id from rides R
        join ride_geo G on G.ride_id = R.id
        left join ride_weather W on W.ride_id = R.id
        where W.ride_id is null;
        """)
    
    api_key = app.config['NCDC_API_KEY']
    c = ncdc_api.Client(token=api_key, cache_dir=app.config['NCDC_CACHE_DIR'])
    
    rx = re.compile('^POINT\((.+)\)$')
    
    rows = db.engine.execute(q).fetchall() # @UndefinedVariable
    for i,r in enumerate(rows):
        ride =  db.session.query(model.Ride).get(r['id']) # @UndefinedVariable
        
        start_geo_wkt = db.session.scalar(ride.geo.start_geo.wkt) # @UndefinedVariable
        
        (lat,lon) = rx.match(start_geo_wkt).group(1).split(' ')
        
        search_results = c.locationsearch(lat=lat, lon=lon, radius=80)
        desired_data = ncdc_model.DesiredObservations(['TMIN', 'TMAX', 'PRCP', 'SNOW'])
        desired_date = ride.start_date
        
        for r in search_results.results:
            still_needed = desired_data.observations_needed
            if not still_needed:
                break
            else:
                logger.debug("Still need: {0!r}".format(still_needed))
                
            if r.type == 'station':
                if desired_date <= r.maxDate and desired_date >= r.minDate:
                    logger.debug("Getting station data for {0!r}".format(r))
                    coll = c.station_data(station=r.id, date=desired_date)
                    desired_data.fill(coll)
                else:
                    logger.debug("Skipping station {0!r} because date doesn't match.".format(r))
        else:
            if desired_data.attributes_wanted == desired_data.observations_needed:
                logger.error("Unable to find weather for ride: {0!r}".format(ride,))
            else:
                logger.info("Exhausted search without filling observations.  (missing = %r)" % (desired_data.observations_needed,))
        
        def _c_to_f(ncdc_temp):
            if ncdc_temp is None:
                return None
            celcius = ncdc_temp / 10.0
            return  int(9.0/5 * (celcius + 32))
        
        def _tenthmm_to_in(tenthmm):
            if tenthmm is None: return None
            mm = tenthmm/10.0
            return mm * 0.0393701
        
        def _mm_to_in(mm):
            if mm is None: return None
            return mm * 0.0393701
        
        rw = model.RideWeather()
        rw.ride_id = ride.id
        prcp = desired_data.observations.get('PRCP')
        snow = desired_data.observations.get('SNOW')
        tmin = desired_data.observations.get('TMIN')
        tmax = desired_data.observations.get('TMAX')
        
        convert = lambda observation, convert_f: convert_f(observation.value) if (observation and observation.value is not None) else None
        
        rw.daily_prcp = convert(prcp, _tenthmm_to_in)
        rw.daily_snow = convert(snow, _mm_to_in)
        rw.daily_tmin = convert(tmin, _c_to_f)
        rw.daily_tmax = convert(tmax, _c_to_f)
        
        db.session.add(rw) #  @UndefinedVariable
        
        db.session.commit()