from instagram import InstagramAPIError

from freezing.model import meta, orm
from freezing.web import data
from freezing.web.scripts import BaseCommand
from freezing.web.utils.insta import configured_instagram_client, photo_cache_path


class SyncPhotos(BaseCommand):
    @property
    def name(self):
        return 'sync-photos'

    def build_parser(self):
        parser = super(SyncPhotos, self).build_parser()
        #
        # parser.add_option("--rewrite", action="store_true", dest="rewrite", default=False,
        #                   help="Whether to rewrite the ride photo data already in database.")

        return parser

    def execute(self, options, args):

        # if options.rewrite:
        #     meta.engine.execute(orm.RidePhoto.__table__.delete())
        #     meta.session_factory().query(orm.Ride).update({"photos_fetched": False})
        sess = meta.session_factory()

        q = sess.query(orm.Ride)
        q = q.filter_by(photos_fetched=False, private=False)

        for ride in q:
            self.logger.info("Writing out photos for {0!r}".format(ride))
            client = data.StravaClientForAthlete(ride.athlete)
            try:

                activity_photos = client.get_activity_photos(ride.id, only_instagram=True)
                """ :type: list[stravalib.orm.ActivityPhoto] """
                data.write_ride_photos_nonprimary(activity_photos, ride)

                sess.commit()
            except:
                sess.rollback()
                self.logger.exception("Error fetching/writing non-primary photos activity {0}, athlete {1}".format(ride.id, ride.athlete))

def main():
    SyncPhotos().run()


if __name__ == '__main__':
    main()