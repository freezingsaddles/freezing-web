from datetime import timedelta, datetime

from pytz import utc
from sqlalchemy import and_

from freezing.model import meta, orm
from freezing.web import app, data
from freezing.web.scripts import BaseCommand
from freezing.web.utils.dates import parse_competition_timestamp
from freezing.web.exc import CommandError, InvalidAuthorizationToken


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
                          help="Whether to rewrite the ride data already in database (does not incur additional API calls).")

        parser.add_option("--force", action="store_true", dest="force", default=False,
                          help="Whether to force the sync (e.g. if after competition end).")

        return parser

    def execute(self, options, args):

        sess = meta.scoped_session()

        if options.start_date:
            start = parse_competition_timestamp(options.start_date)
            self.logger.info("Fetching rides newer than {0}".format(start))
        else:
            start = None
            self.logger.info("Fetching all rides (since competition start)")

        end_date = parse_competition_timestamp(app.config['BAFS_END_DATE'])
        grace_days = app.config['BAFS_UPLOAD_GRACE_PERIOD_DAYS']
        grace_delta = timedelta(days=grace_days)

        if (datetime.now(utc) > (end_date + grace_delta)) and not options.force:
            raise CommandError("Current time is after competition end date + grace period, not syncing rides. (Use --force to override.)")

        if options.rewrite:
            self.logger.info("Rewriting existing ride data.")

        # We iterate over all of our athletes that have access tokens.  (We can't fetch anything
        # for those that don't.)
        q = sess.query(orm.Athlete)
        q = q.filter(orm.Athlete.access_token != None)

        if options.athlete_id:
            q = q.filter(orm.Athlete.id == options.athlete_id)

        # Also only fetch athletes that have teams configured.  This may not be strictly necessary
        # but this is a team competition, so not a lot of value in pulling in data for those
        # without teams.
        # (The way the athlete sync works, athletes will only be configured for a single team
        # that is one of the configured competition teams.)
        q = q.filter(orm.Athlete.team_id != None)

        for athlete in q.all():
            assert isinstance(athlete, orm.Athlete)
            self.logger.info("Fetching rides for athlete: {0}".format(athlete))
            try:
                self._write_rides(start, end_date, athlete=athlete, rewrite=options.rewrite)
            except InvalidAuthorizationToken:
                self.logger.error("Invalid authorization token for {} (removing)".format(athlete))
                athlete.access_token = None
                sess.add(athlete)

        sess.commit()

    def _write_rides(self, start, end, athlete, rewrite=False):

        sess = meta.scoped_session()

        api_ride_entries = data.list_rides(athlete=athlete, start_date=start, end_date=end,
                                           exclude_keywords=app.config.get('BAFS_EXCLUDE_KEYWORDS'))

        start_notz = start.replace(
            tzinfo=None)  # Because MySQL doesn't like it and we are not storing tz info in the db.

        q = sess.query(orm.Ride)
        q = q.filter(and_(orm.Ride.athlete_id == athlete.id,
                          orm.Ride.start_date >= start_notz))
        db_rides = q.all()

        # Quickly filter out only the rides that are not in the database.
        returned_ride_ids = set([r.id for r in api_ride_entries])
        stored_ride_ids = set([r.id for r in db_rides])
        new_ride_ids = list(returned_ride_ids - stored_ride_ids)
        removed_ride_ids = list(stored_ride_ids - returned_ride_ids)

        num_rides = len(api_ride_entries)

        for (i, strava_activity) in enumerate(api_ride_entries):
            self.logger.debug("Processing ride: {0} ({1}/{2})".format(strava_activity.id, i + 1, num_rides))

            if rewrite or not strava_activity.id in stored_ride_ids:
                try:
                    ride = data.write_ride(strava_activity)
                    self.logger.info("[NEW RIDE]: {id} {name!r} ({i}/{num}) ".format(id=strava_activity.id,
                                                                                     name=strava_activity.name,
                                                                                     i=i + 1,
                                                                                     num=num_rides))
                    sess.commit()
                except Exception as x:
                    self.logger.debug("Error writing out ride, will attempt to add/update RideError: {0}".format(strava_activity.id))
                    sess.rollback()
                    try:
                        ride_error = sess.query(orm.RideError).get(strava_activity.id)
                        if ride_error is None:
                            self.logger.exception("[ERROR] Unable to write ride (skipping): {0}".format(strava_activity.id))
                            ride_error = orm.RideError()
                        else:
                            # We already have a record of the error, so log that message with less verbosity.
                            self.logger.warning("[ERROR] Unable to write ride (skipping): {0}".format(strava_activity.id))

                        ride_error.athlete_id = athlete.id
                        ride_error.id = strava_activity.id
                        ride_error.name = strava_activity.name
                        ride_error.start_date = strava_activity.start_date_local
                        ride_error.reason = str(x)
                        ride_error.last_seen = datetime.now()  # FIXME: TZ?
                        sess.add(ride_error)

                        sess.commit()
                    except:
                        self.logger.exception("Error adding ride-error entry.")
                else:
                    sess.commit()
                    try:
                        # If there is an error entry, then we should remove it.
                        q = sess.query(orm.RideError)
                        q = q.filter(orm.RideError.id == ride.id)
                        deleted = q.delete(synchronize_session=False)
                        if deleted:
                            self.logger.info("Removed matching error-ride entry for {0}".format(strava_activity.id))
                        sess.commit()
                    except:
                        self.logger.exception("Error maybe-clearing ride-error entry.")
            else:
                self.logger.info("[SKIPPED EXISTING]: {id} {name!r} ({i}/{num}) ".format(id=strava_activity.id,
                                                                                         name=strava_activity.name,
                                                                                         i=i + 1,
                                                                                         num=num_rides))

        # Remove any rides that are in the database for this athlete that were not in the returned list.
        if removed_ride_ids:
            q = sess.query(orm.Ride)
            q = q.filter(orm.Ride.id.in_(removed_ride_ids))
            deleted = q.delete(synchronize_session=False)
            self.logger.info("Removed {0} no longer present rides for athlete {1}.".format(deleted, athlete))
        else:
            self.logger.info("(No removed rides for athlete {0}.)".format(athlete))

        sess.commit()


def main():
    SyncRides().run()


if __name__ == '__main__':
    main()