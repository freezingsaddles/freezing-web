import optparse
import logging

from dateutil import parser as dateutil_parser
from sqlalchemy import not_, and_, text

from bafs import app, db
from bafs import data, model

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
        athlete = sess.query(model.Athlete).get(athlete_id)
        logger.info("Fetching rides for athlete: {0}".format(athlete))
        _write_rides(start, athlete=athlete)

def _write_rides(start, team=None, athlete=None):
    
    logger = logging.getLogger('sync')
    
    if team and athlete:
        raise ValueError("team and athlete params are mutually exclusive")
    elif team is None and athlete is None:
        raise ValueError("either team or athlete param is required")
    
    sess = db.session
    
    if team:
        api_ride_entries = data.list_rides(club_id=team.id, start_date=start, exclude_keywords=app.config.get('BAFS_EXCLUDE_KEYWORDS'))
        q = sess.query(model.Ride)
        q = q.filter(and_(model.Ride.athlete_id.in_(sess.query(model.Athlete.id).filter(model.Athlete.team_id==team.id)),
                          model.Ride.start_date >= start))
        db_rides = q.all()
    else:
        api_ride_entries = data.list_rides(athlete_id=athlete.id, start_date=start, exclude_keywords=app.config.get('BAFS_EXCLUDE_KEYWORDS'))
        db_rides = athlete.rides.filter(model.Ride.start_date >= start).all()
    
    # Quickly filter out only the rides that are not in the database.
    returned_ride_ids = set([r.id for r in api_ride_entries])
    stored_ride_ids = set([r.id for r in db_rides])
    new_ride_ids = list(returned_ride_ids - stored_ride_ids)
    removed_ride_ids = list(stored_ride_ids - returned_ride_ids)
    num_rides = len(new_ride_ids)
    
    for (i, ri_entry) in enumerate([r_i for r_i in api_ride_entries if r_i.id in new_ride_ids]):
        logger.info("Processing ride: {0} ({1}/{2})".format(ri_entry.id, i, num_rides))
        if not sess.query(model.Ride).get(ri_entry.id):
            ride = data.write_ride(ri_entry.id, team=team)
            logger.debug("Wrote new ride: %r" % (ride,))
        else:
            logger.debug("Skipping existing ride: {id} - {name!r}".format(name=ri_entry.name,id=ri_entry.id))

    # Remove any rides that are in the database for this team that were not in the returned list.
    q = sess.query(model.Ride)
    q = q.filter(model.Ride.id.in_(removed_ride_ids))
    deleted = q.delete(synchronize_session=False)
    if team:
        logger.info("Removed {0} no longer present rides for team {1}.".format(deleted, team.id))
    else:
        logger.info("Removed {0} no longer present rides for athlete {1}.".format(deleted, athlete.id))
                    
    sess.commit() 
        
    # Write out any efforts associated with these rides (not already in database)
    q = sess.query(model.Ride).filter_by(efforts_fetched=False)
    for ride in q.all():
        logger.info("Writing out efforts for {0!r}".format(ride))
        data.write_ride_efforts(ride)
    
def sync_ride_efforts():
    """
    Syncs up the ride_efforts table.
    (This must be run after rides have already been sychronized.)
    """
    parser = optparse.OptionParser()
        
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
    logger = logging.getLogger('sync-efforts')
    
    sess = db.session
    
    if options.clear:
        logger.info("Clearing all data!")
        sess.query(model.RideEffort).delete()
        
    
    all_rides = sess.query(model.Ride).where().all()
    
    if not all_rides:
        raise RuntimeError("No rides have been loaded yet")
    
    for ride in all_rides:
        logger.info("Writing out efforts for {0!r}".format(ride))
        data.write_ride_efforts(ride.id)