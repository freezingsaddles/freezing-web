import os
import sys
import optparse
import logging
import re
import time
from datetime import datetime, timedelta
from pprint import pprint

from dateutil import parser as dateutil_parser
from sqlalchemy import not_, and_, text
from pytz import timezone, utc
from requests.exceptions import HTTPError

from alembic.config import Config
from alembic import command

from bafs.utils.insta import configured_instagram_client, photo_cache_path
from instagram import InstagramAPIError
 
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
    
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.stamp(alembic_cfg, "head")

    
def sync_rides():
    """
    Synchronize rides from strava with the database.
    """
    parser = optparse.OptionParser()
    
    parser.add_option("--start-date", dest="start_date",
                      help="Date to begin fetching (default is to fetch all since configured start date)",
                      default=app.config['BAFS_START_DATE'],
                      metavar="YYYY-MM-DD")

    parser.add_option("--athlete-id", dest="athlete_id",
                      help="Just sync rides for a specific athlete.",
                      metavar="STRAVA_ID")

    parser.add_option("--rewrite", action="store_true", dest="rewrite", default=False, 
                      help="Whether to rewrite the ride data already in database.")
    
    parser.add_option("--debug", action="store_true", dest="debug", default=False, 
                      help="Whether to log at debug level.")
    
    parser.add_option("--quiet", action="store_true", dest="quiet", default=False, 
                      help="Whether to suppress non-error log output.")
    
    parser.add_option("--force", action="store_true", dest="force", default=False, 
                      help="Whether to force the sync (e.g. if after competition end).")
    
    (options, args) = parser.parse_args()
    
    if options.quiet:
        loglevel = logging.ERROR
    elif options.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
        
    logging.basicConfig(level=loglevel)
    logger = logging.getLogger('sync-rides')
    
    sess = db.session
    
    if options.start_date:
        start = dateutil_parser.parse(options.start_date)
        logger.info("Fetching rides newer than {0}".format(start))
    else:
        start=None
        logger.info("Fetching all rides (since competition start)")
    
    end_date = dateutil_parser.parse(app.config['BAFS_END_DATE'])
    grace_days = app.config['BAFS_UPLOAD_GRACE_PERIOD_DAYS']
    grace_delta = timedelta(days=grace_days)

    if (datetime.now(utc) > (end_date + grace_delta)) and not options.force:
        parser.error("Current time is after competition end date + grace period, not syncing rides. (Use --force to override.)")
        sys.exit(1)
        
    if options.rewrite:
        logger.info("Rewriting existing ride data.")
    
    # We iterate over all of our athletes that have access tokens.  (We can't fetch anything
    # for those that don't.)
    q = sess.query(model.Athlete)
    q = q.filter(model.Athlete.access_token != None)

    if options.athlete_id:
        q = q.filter(model.Athlete.id == options.athlete_id)

    # Also only fetch athletes that have teams configured.  This may not be strictly necessary
    # but this is a team competition, so not a lot of value in pulling in data for those
    # without teams.
    # (The way the athlete sync works, athletes will only be configured for a single team
    # that is one of the configured competition teams.)
    q = q.filter(model.Athlete.team_id != None)
    
    for athlete in q.all():
        logger.info("Fetching rides for athlete: {0}".format(athlete))
        _write_rides(start, end_date, athlete=athlete, rewrite=options.rewrite)

def _write_rides(start, end, athlete, rewrite=False):
    
    logger = logging.getLogger('sync-rides')
    
    sess = db.session
    
    api_ride_entries = data.list_rides(athlete=athlete, start_date=start, end_date=end, exclude_keywords=app.config.get('BAFS_EXCLUDE_KEYWORDS'))

    start_notz = start.replace(tzinfo=None) # Because MySQL doesn't like it and we are not storing tz info in the db.

    q = sess.query(model.Ride)
    q = q.filter(and_(model.Ride.athlete_id == athlete.id,
                      model.Ride.start_date >= start_notz))
    db_rides = q.all()

    # Quickly filter out only the rides that are not in the database.
    returned_ride_ids = set([r.id for r in api_ride_entries])
    stored_ride_ids = set([r.id for r in db_rides])
    new_ride_ids = list(returned_ride_ids - stored_ride_ids)
    removed_ride_ids = list(stored_ride_ids - returned_ride_ids)
    
    num_rides = len(api_ride_entries)
    #if rewrite:
    #    num_rides = len(api_ride_entries)
    #else:
    #    num_rides = len(new_ride_ids)
    
    segment_sync_queue = []
    photo_sync_queue = []
    for (i, strava_activity) in enumerate(api_ride_entries):
        logger.debug("Preparing to process ride: {0} ({1}/{2})".format(strava_activity.id, i+1, num_rides))
        try:
            if rewrite or not strava_activity.id in stored_ride_ids:
                (ride, resync_segments, resync_photos) = data.write_ride(strava_activity)
                if resync_segments:
                    segment_sync_queue.append(ride)
                if resync_photos:
                    photo_sync_queue.append(ride)
                logger.info("[NEW RIDE]: {id} {name!r} ({i}/{num}) ".format(id=strava_activity.id,
                                                                           name=strava_activity.name,
                                                                           i=i+1,
                                                                           num=num_rides))
            else:
                logger.info("[SKIPPED EXISTING]: {id} {name!r} ({i}/{num}) ".format(id=strava_activity.id,
                                                                                   name=strava_activity.name,
                                                                                   i=i+1,
                                                                                   num=num_rides))
        except:
            logger.exception("Unable to write ride (skipping): {0}".format(strava_activity.id))
            sess.rollback()
        else:
            sess.commit()
            
    # Remove any rides that are in the database for this athlete that were not in the returned list.
    if removed_ride_ids:
        q = sess.query(model.Ride)
        q = q.filter(model.Ride.id.in_(removed_ride_ids))
        deleted = q.delete(synchronize_session=False)
        logger.info("Removed {0} no longer present rides for athlete {1}.".format(deleted, athlete))
    else:
        logger.info("(No removed rides for athlete {0}.)".format(athlete))
    
    sess.commit() 
     
    # TODO: This could be its own function, really
    # Write out any efforts associated with these rides (not already in database)
    for ride in segment_sync_queue:
        logger.info("Writing out efforts for {0!r}".format(ride))
        client = data.StravaClientForAthlete(ride.athlete)
        try:
            strava_activity = client.get_activity(ride.id)
            data.write_ride_efforts(strava_activity, ride)
        except:
            logger.exception("Error fetching/writing activity {0}, athlete {1}".format(ride.id, athlete))

    # TODO: This could (also) be its own function, really
    # TODO: This could be more intelligently combined with the efforts (save at least 1 API call per activity)
    # Write out any photos associated with these rides (not already in database)
    # for ride in photo_sync_queue:
    #     logger.info("Writing out photos for {0!r}".format(ride))
    #     client = data.StravaClientForAthlete(ride.athlete)
    #     try:
    #         strava_activity = client.get_activity(ride.id)
    #         data.write_ride_photos(strava_activity, ride)
    #     except:
    #         logger.exception("Error fetching/writing activity {0}, athlete {1}".format(ride.id, athlete))
    #

def sync_photos():
    """
    Grabs photos associated with strava activities.
    """

    logger = logging.getLogger('sync-photos')

    parser = optparse.OptionParser()

    parser.add_option("--rewrite", action="store_true", dest="rewrite", default=False,
                      help="Whether to rewrite the ride photo data already in database.")

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

    if options.rewrite:
        db.engine.execute(model.RidePhoto.__table__.delete())
        db.session.query(model.Ride).update({"photos_fetched": False})

    q = db.session.query(model.Ride)
    q = q.filter(model.Ride.photos_fetched==False)

    for ride in q:
        logger.info("Writing out photos for {0!r}".format(ride))
        client = data.StravaClientForAthlete(ride.athlete)
        insta_client = configured_instagram_client()
        try:
            try:
                # Start by removing any existing photos for the ride.
                if not options.rewrite:
                    # (This would be redundant if we already cleared the entire table.)
                    db.engine.execute(model.RidePhoto.__table__.delete().where(model.RidePhoto.ride_id==ride.id))

                # Add the photos for this activity.
                for p in client.get_activity_photos(ride.id):
                    try:
                        # TODO: Make caching configurable?
                        photo_cache_path(p.uid)

                        photo = model.RidePhoto(id=p.id,
                                                ride_id=ride.id,
                                                ref=p.ref,
                                                caption=p.caption,
                                                uid=p.uid)

                        logger.debug("Writing ride photo: {p_id}: {photo!r}".format(p_id=p.id,
                                                                                    photo=photo))
                        db.session.merge(photo)
                    except InstagramAPIError as e:
                        if e.status_code == 400:
                            logger.debug("Skipping photo {0} for ride {1}; user is set to private".format(p, ride))
                        else:
                            logger.exception("Error fetching instagram photo {0}".format(p))

                ride.photos_fetched = True
                db.session.commit() # @UndefinedVariable
            except:
                logger.exception("Error adding photo for ride: {0}".format(ride))
                continue
        except:
            logger.exception("Error fetching/writing activity {0}, athlete {1}".format(ride.id, ride.athlete))

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
    logger = logging.getLogger('sync-weather')
    
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
        where W.ride_id is null
        and date(R.start_date) < CURDATE()
        and time(R.start_date) != '00:00:00' -- Exclude bad entries. 
        ;
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
        
        ride =  sess.query(model.Ride).get(r['id'])
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
                # if we dont' have many observations, bookend the list with the start/end observations
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
                    # But soldier on ...
        except:
            logger.exception("Error getting weather data for ride: {0}".format(ride))
            # But soldier on ...
            
    sess.commit() 

    
def sync_athletes():
    """
    Updates the athlete records, and associates with teams.
    
    (Designed to be run periodically to ensure that things like names and team
    membership are kept in sync w/ Strava.)
    """
    parser = optparse.OptionParser()
    
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
    logger = logging.getLogger('sync-athletes')
    
    sess = db.session
    
    # We iterate over all of our athletes that have access tokens.  (We can't fetch anything
    # for those that don't.)
    
    q = sess.query(model.Athlete)
    q = q.filter(model.Athlete.access_token != None)
    
    for athlete in q.all():
        logger.info("Updating athlete: {0}".format(athlete))
        c = data.StravaClientForAthlete(athlete)
        strava_athlete = c.get_athlete()
        try:
            data.register_athlete(strava_athlete, athlete.access_token)
            data.register_athlete_team(strava_athlete, athlete)
        except:
            logger.warning("Error registering athlete {0}".format(athlete), exc_info=True)
            # But carry on
            
    data.disambiguate_athlete_display_names()
