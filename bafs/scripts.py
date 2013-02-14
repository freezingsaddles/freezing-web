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
    
    (options, args) = parser.parse_args()
    
    logging.basicConfig(level=logging.DEBUG if options.debug else logging.INFO)
    logger = logging.getLogger('sync')
    
    sess = db.session
    
    if options.start_date:
        start = dateutil_parser.parse(options.start_date)
        logger.info("Fetching rides newer than {0}".format(start))
    else:
        start=None
        logger.info("Fetching all rides")
    
    if options.clear:
        logger.info("Clearing all data!")
        sess.query(model.RideGeo).delete()
        sess.query(model.Ride).delete()
        sess.query(model.Athlete).delete()
        sess.query(model.Team).delete()
        
    for club_id in app.config['BAFS_TEAMS']:
        team = model.Team(id=club_id,
                          name=data.get_team_name(club_id))
        sess.merge(team)
        sess.commit()
        
        logger.info("Fetching rides for team: {name!r} ({id})".format(name=team.name, id=team.id))
        rides = data.list_rides(club_id=club_id, start_date=start, exclude_keywords=app.config.get('BAFS_EXCLUDE_KEYWORDS'))
        num_rides = len(rides)
        for (i, ri_entry) in enumerate(rides):
            logger.info("Processing ride: {0} ({1}/{2})".format(ri_entry.id, i, num_rides))
            if not sess.query(model.Ride).get(ri_entry.id):
                ride = data.write_ride(team, ri_entry.id)
                logger.debug("Wrote new ride: %r" % (ride,))
            else:
                logger.debug("Skipping existing ride: {id} - {name!r}".format(name=ri_entry.name,id=ri_entry.id))

        # Remove any rides that are in the database for this team that were not in the returned list.
        ride_ids = [r.id for r in rides]
        q = sess.query(model.Ride)
        q = q.filter(and_(not_(model.Ride.id.in_(ride_ids)),
                          model.Ride.athlete_id.in_(sess.query(model.Athlete.id).filter(model.Athlete.team_id==club_id)),
                          model.Ride.start_date >= start))
        deleted = q.delete(synchronize_session=False)
        logger.info("Removed {0} no longer present rides.".format(deleted))
        sess.commit() 
        
    # TODO: Add support for the unattached riders.
    