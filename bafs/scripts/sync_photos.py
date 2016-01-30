from instagram import InstagramAPIError

from bafs import db, model, data
from bafs.scripts import BaseCommand
from bafs.utils.insta import configured_instagram_client, photo_cache_path


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
        #     db.engine.execute(model.RidePhoto.__table__.delete())
        #     db.session.query(model.Ride).update({"photos_fetched": False})

        q = db.session.query(model.Ride)
        q = q.filter_by(photos_fetched=False, private=False)

        for ride in q:
            self.logger.info("Writing out photos for {0!r}".format(ride))
            client = data.StravaClientForAthlete(ride.athlete)
            try:

                activity_photos = client.get_activity_photos(ride.id)
                """ :type: list[stravalib.model.ActivityPhoto] """
                data.write_ride_photos_nonprimary(activity_photos, ride)

                db.session.commit()
            except:
                db.session.rollback()
                self.logger.exception("Error fetching/writing non-primary photos activity {0}, athlete {1}".format(ride.id, ride.athlete))

def main():
    SyncPhotos().run()


if __name__ == '__main__':
    main()