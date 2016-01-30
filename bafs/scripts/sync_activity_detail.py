import os
import json
import logging

from geoalchemy import WKTSpatialElement
from polyline.codec import PolylineCodec
from sqlalchemy import update, or_, and_

from stravalib import model as stravamodel

from bafs import db, model, data, app
from bafs.model import Ride, RideTrack, RidePhoto
from bafs.scripts import BaseCommand
from bafs.utils.insta import configured_instagram_client, photo_cache_path
from bafs.exc import ConfigurationError
from bafs.autolog import log


class SyncActivityDetails(BaseCommand):
    @property
    def name(self):
        return 'sync-activity-detail'

    def build_parser(self):
        parser = super(SyncActivityDetails, self).build_parser()
        parser.add_option("--athlete-id", dest="athlete_id",
                          help="Just sync rides for a specific athlete.",
                          metavar="STRAVA_ID")
        parser.add_option("--use-cache", action="store_true", dest="use_cache", default=False,
                          help="Whether to use cached activities (rather than refetch from server).")

        return parser

    def cache_dir(self, athlete_id):
        """
        Gets the cache directory for specific athlete.
        :param athlete_id: The athlete ID.
        :type athlete_id: int | str
        :return: The cache directory.
        :rtype: str
        """
        cache_basedir = app.config['STRAVA_ACTIVITY_CACHE_DIR']
        if not cache_basedir:
            raise ConfigurationError("STRAVA_ACTIVITY_CACHE_DIR not configured!")

        directory = os.path.join(cache_basedir, str(athlete_id))
        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory

    def cache_activity(self, strava_activity, activity_json):
        """
        Writes activity to cache dir.

        :param strava_activity: The Strava activity
        :type strava_activity: stravalib.model.Activity

        :param activity_json: The raw JSON for the activity.
        :type activity_json: dict
        :return:
        """
        directory = self.cache_dir(strava_activity.athlete.id)

        activity_fname = '{}.json'.format(strava_activity.id)
        cache_path = os.path.join(directory, activity_fname)

        with open(cache_path, 'w') as fp:
            fp.write(json.dumps(activity_json, indent=2))

        return cache_path

    def get_cached_activity_json(self, ride):
        """
        Writes activity to cache dir.

        :param ride: The Ride model object.
        :type ride: bafs.model.Ride

        :return: A matched Strava Activity JSON object or None if there was no cache.
        :rtype: dict
        """
        directory = self.cache_dir(ride.athlete_id)

        activity_fname = '{}.json'.format(ride.id)

        cache_path = os.path.join(directory, activity_fname)

        activity_json = None
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as fp:
                activity_json = json.load(fp)

        return activity_json

    def execute(self, options, args):

        q = db.session.query(model.Ride)

        # TODO: Construct a more complex query to catch photos_fetched=False, track_fetched=False, etc.
        q = q.filter(and_(Ride.detail_fetched==False,
                          Ride.private==False))

        if options.athlete_id:
            self.logger.info("Filtering activity details for {}".format(options.athlete_id))
            q = q.filter(Ride.athlete_id == options.athlete_id)

        self.logger.info("Fetching details for {} activities".format(q.count()))

        for ride in q:
            try:
                client = data.StravaClientForAthlete(ride.athlete)

                # TODO: Make it configurable to force refresh of data.
                activity_json = self.get_cached_activity_json(ride) if options.use_cache else None

                if activity_json is None:
                    self.logger.info("[CACHE-MISS] Fetching activity detail for {!r}".format(ride))
                    # We do this manually, so that we can cache the JSON for later use.
                    activity_json = client.protocol.get('/activities/{id}', id=ride.id, include_all_efforts=True)
                    strava_activity = stravamodel.Activity.deserialize(activity_json, bind_client=client)

                    try:
                        self.logger.info("Caching activity {!r}".format(ride))
                        self.cache_activity(strava_activity, activity_json)
                    except:
                        log.error("Error caching activity {} (ignoring)".format(strava_activity),
                                  exc_info=self.logger.isEnabledFor(logging.DEBUG))

                else:
                    strava_activity = stravamodel.Activity.deserialize(activity_json, bind_client=client)
                    self.logger.info("[CACHE-HIT] Using cached activity detail for {!r}".format(ride))

                try:
                    self.logger.info("Writing out GPS track for {!r}".format(ride))
                    data.write_ride_track(strava_activity, ride)
                except:
                    self.logger.error("Error writing track for activity {0}, athlete {1}".format(ride.id, ride.athlete),
                                      exc_info=self.logger.isEnabledFor(logging.DEBUG))
                    raise

                try:
                    self.logger.info("Writing out efforts for {!r}".format(ride))
                    data.write_ride_efforts(strava_activity, ride)
                except:
                    self.logger.error("Error writing efforts for activity {0}, athlete {1}".format(ride.id, ride.athlete),
                                      exc_info=self.logger.isEnabledFor(logging.DEBUG))
                    raise

                try:
                    self.logger.info("Writing out photos for {!r}".format(ride))
                    if strava_activity.total_photo_count > 0:
                        data.write_ride_photo_primary(strava_activity, ride)
                        # If there are multiple instagram photos, then request syncing of non-primary photos too.
                        if strava_activity.photo_count > 1 and strava_activity.photos_fetched is None:
                            self.logger.debug("Scheduling non-primary photos sync for {!r}".format(ride))
                            ride.photos_fetched = False
                    else:
                        self.logger.debug ("No photos for {!r}".format(ride))
                except:
                    self.logger.error("Error writing primary photo for activity {}, athlete {}".format(ride.id, ride.athlete),
                                      exc_info=self.logger.isEnabledFor(logging.DEBUG))
                    raise

                # TODO: photos.  We need to distinguish between the external photo fetch and those that are present in summary.
                # NB: Only Instagram photos merit an external fetch.

                ride.detail_fetched = True
                db.session.commit()

            except:
                self.logger.exception("Error fetching/writing activity detail {}, athlete {}".format(ride.id, ride.athlete))
                db.session.rollback()


def main():
    SyncActivityDetails().run()


if __name__ == '__main__':
    main()