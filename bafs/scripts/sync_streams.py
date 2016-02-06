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


class SyncActivityStreams(BaseCommand):

    @property
    def name(self):
        return 'sync-activity-streams'

    def build_parser(self):
        parser = super(SyncActivityStreams, self).build_parser()
        parser.add_option("--athlete-id", dest="athlete_id", type="int",
                          help="Just sync streams for a specific athlete.",
                          metavar="STRAVA_ID")

        parser.add_option("--max-records", dest="max_records", type="int",
                          help="Limit number of activities to return.",
                          metavar="NUM")

        parser.add_option("--use-cache", action="store_true", dest="use_cache", default=False,
                          help="Whether to use cached streams (rather than refetch from server).")

        parser.add_option("--only-cache", action="store_true", dest="only_cache", default=False,
                          help="Whether to use only cached streams (rather than fetch anything from server).")

        parser.add_option("--rewrite", action="store_true", dest="rewrite", default=False,
                          help="Whether to re-store all streams.")

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

    def cache_stream(self, ride, activity_json):
        """
        Write streams to cache dir.

        :param ride: The Ride model object.
        :type ride: bafs.model.Ride

        :param activity_json: The raw JSON for the activity.
        :type activity_json: dict
        :return:
        """
        directory = self.cache_dir(ride.athlete_id)

        streams_fname = '{}_streams.json'.format(ride.id)
        cache_path = os.path.join(directory, streams_fname)

        with open(cache_path, 'w') as fp:
            fp.write(json.dumps(activity_json, indent=2))

        return cache_path

    def get_cached_streams_json(self, ride):
        """
        Get the cached streams JSON for specified ride.

        :param ride: The Ride model object.
        :type ride: bafs.model.Ride

        :return: A matched Strava Activity JSON object or None if there was no cache.
        :rtype: dict
        """
        directory = self.cache_dir(ride.athlete_id)

        streams_fname = '{}_streams.json'.format(ride.id)

        cache_path = os.path.join(directory, streams_fname)

        streams_json = None
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as fp:
                streams_json = json.load(fp)

        return streams_json

    def execute(self, options, args):

        q = db.session.query(model.Ride)

        # TODO: Construct a more complex query to catch photos_fetched=False, track_fetched=False, etc.
        q = q.filter(and_(Ride.private==False,
                          Ride.manual==False))

        if not options.rewrite:
            q = q.filter(Ride.track_fetched==False,)

        if options.athlete_id:
            self.logger.info("Filtering activity details for {}".format(options.athlete_id))
            q = q.filter(Ride.athlete_id == options.athlete_id)

        if options.max_records:
            self.logger.info("Limiting to {} records".format(options.max_records))
            q = q.limit(options.max_records)

        use_cache = options.use_cache or options.only_cache

        self.logger.info("Fetching gps tracks for {} activities".format(q.count()))

        for ride in q:
            try:
                client = data.StravaClientForAthlete(ride.athlete)

                # TODO: Make it configurable to force refresh of data.
                streams_json = self.get_cached_streams_json(ride) if use_cache else None

                if streams_json is None:
                    if options.only_cache:
                        self.logger.info("[CACHE-MISS] Skipping ride {} since there is no cached stream.".format(ride))
                        continue

                    self.logger.info("[CACHE-MISS] Fetching streams for {!r}".format(ride))

                    # We do this manually, so that we can cache the JSON for later use.
                    streams_json = client.protocol.get(
                            '/activities/{id}/streams/{types}'.format(id=ride.id, types='latlng,time,altitude'),
                            resolution='low'
                    )

                    streams = [stravamodel.Stream.deserialize(stream_struct, bind_client=client) for stream_struct in streams_json]

                    try:
                        self.logger.info("Caching streams for {!r}".format(ride))
                        self.cache_stream(ride, streams_json)
                    except:
                        log.error("Error caching streams for activity {} (ignoring)".format(ride),
                                  exc_info=self.logger.isEnabledFor(logging.DEBUG))

                else:
                    streams = [stravamodel.Stream.deserialize(stream_struct, bind_client=client) for stream_struct in streams_json]
                    self.logger.info("[CACHE-HIT] Using cached streams detail for {!r}".format(ride))

                data.write_ride_streams(streams, ride)

                db.session.commit()
            except:
                self.logger.exception("Error fetching/writing activity streams for {}, athlete {}".format(ride, ride.athlete))
                db.session.rollback()


def main():
    SyncActivityStreams().run()


if __name__ == '__main__':
    main()