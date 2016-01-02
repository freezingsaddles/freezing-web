from datetime import timedelta, datetime

from pytz import utc
from sqlalchemy import and_
from dateutil import parser as dateutil_parser

from bafs import app, db, model, data
from bafs.scripts import BaseCommand, CommandError


class SyncRides(BaseCommand):
    """
    Synchronize rides from strava with the database.
    """

    @property
    def name(self):
        return 'sync-rides'

    def build_parser(self):
        parser = super(SyncRides, self).build_parser()

        parser.add_option("--start-date", dest="start_date",
                          help="Date to begin fetching (default is to fetch all since configured start date)",
                          default=app.config['BAFS_START_DATE'],
                          metavar="YYYY-MM-DD")

        parser.add_option("--athlete-id", dest="athlete_id",
                          help="Just sync rides for a specific athlete.",
                          metavar="STRAVA_ID")

        parser.add_option("--rewrite", action="store_true", dest="rewrite", default=False,
                          help="Whether to rewrite the ride data already in database.")

        parser.add_option("--force", action="store_true", dest="force", default=False,
                          help="Whether to force the sync (e.g. if after competition end).")

        return parser

    def execute(self, options, args):

        sess = db.session

        if options.start_date:
            start = dateutil_parser.parse(options.start_date)
            self.logger.info("Fetching rides newer than {0}".format(start))
        else:
            start = None
            self.logger.info("Fetching all rides (since competition start)")

        end_date = dateutil_parser.parse(app.config['BAFS_END_DATE'])
        grace_days = app.config['BAFS_UPLOAD_GRACE_PERIOD_DAYS']
        grace_delta = timedelta(days=grace_days)

        if (datetime.now(utc) > (end_date + grace_delta)) and not options.force:
            raise CommandError("Current time is after competition end date + grace period, not syncing rides. (Use --force to override.)")

        if options.rewrite:
            self.logger.info("Rewriting existing ride data.")

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
            self.logger.info("Fetching rides for athlete: {0}".format(athlete))
            self._write_rides(start, end_date, athlete=athlete, rewrite=options.rewrite)

    def _write_rides(self, start, end, athlete, rewrite=False):

        sess = db.session

        api_ride_entries = data.list_rides(athlete=athlete, start_date=start, end_date=end,
                                           exclude_keywords=app.config.get('BAFS_EXCLUDE_KEYWORDS'))

        start_notz = start.replace(
            tzinfo=None)  # Because MySQL doesn't like it and we are not storing tz info in the db.

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
        # if rewrite:
        #    num_rides = len(api_ride_entries)
        # else:
        #    num_rides = len(new_ride_ids)

        segment_sync_queue = []
        photo_sync_queue = []
        for (i, strava_activity) in enumerate(api_ride_entries):
            self.logger.debug("Preparing to process ride: {0} ({1}/{2})".format(strava_activity.id, i + 1, num_rides))
            try:
                if rewrite or not strava_activity.id in stored_ride_ids:
                    (ride, resync_segments, resync_photos) = data.write_ride(strava_activity)
                    self.logger.info("[NEW RIDE]: {id} {name!r} ({i}/{num}) ".format(id=strava_activity.id,
                                                                                     name=strava_activity.name,
                                                                                     i=i + 1,
                                                                                     num=num_rides))
                    if not strava_activity.private:
                        if resync_segments:
                            segment_sync_queue.append(ride)
                        if resync_photos:
                            photo_sync_queue.append(ride)
                    else:
                        self.logger.info("[PRIVATE RIDE]: {id} is private, no segments/photos can be fetched.".format(
                            id=strava_activity.id))
                        ride.photos_fetched = True
                        ride.efforts_fetched = True
                else:
                    self.logger.info("[SKIPPED EXISTING]: {id} {name!r} ({i}/{num}) ".format(id=strava_activity.id,
                                                                                             name=strava_activity.name,
                                                                                             i=i + 1,
                                                                                             num=num_rides))
            except:
                self.logger.exception("Unable to write ride (skipping): {0}".format(strava_activity.id))
                sess.rollback()
            else:
                sess.commit()

        # Remove any rides that are in the database for this athlete that were not in the returned list.
        if removed_ride_ids:
            q = sess.query(model.Ride)
            q = q.filter(model.Ride.id.in_(removed_ride_ids))
            deleted = q.delete(synchronize_session=False)
            self.logger.info("Removed {0} no longer present rides for athlete {1}.".format(deleted, athlete))
        else:
            self.logger.info("(No removed rides for athlete {0}.)".format(athlete))

        sess.commit()

        # TODO: This could be its own function, really
        # Write out any efforts associated with these rides (not already in database)
        for ride in segment_sync_queue:
            self.logger.info("Writing out efforts for {0!r}".format(ride))
            client = data.StravaClientForAthlete(ride.athlete)
            try:
                strava_activity = client.get_activity(ride.id)
                data.write_ride_efforts(strava_activity, ride)
            except:
                self.logger.exception(
                    "Unexpected error fetching/writing activity {0}, athlete {1}".format(ride.id, athlete))

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


def main():
    SyncRides().run()