from instagram import InstagramAPIError

from bafs.autolog import log
from bafs import db, model, data
from bafs.scripts import BaseCommand
from bafs.utils.insta import configured_instagram_client


class FixPhotoUrls(BaseCommand):
    @property
    def name(self):
        return 'sync-photos'

    def build_parser(self):
        parser = super(FixPhotoUrls, self).build_parser()
        #
        # parser.add_option("--rewrite", action="store_true", dest="rewrite", default=False,
        #                   help="Whether to rewrite the ride photo data already in database.")

        return parser

    def execute(self, options, args):

        # if options.rewrite:
        #     db.engine.execute(model.RidePhoto.__table__.delete())
        #     db.session.query(model.Ride).update({"photos_fetched": False})

        q = db.session.query(model.RidePhoto)
        q = q.filter_by(img_t=None)

        insta_client = configured_instagram_client()

        del_q = []
        for ride_photo in q:
            self.logger.debug("Updating URLs for photo {}".format(ride_photo))
            try:
                media = insta_client.media(ride_photo.id)
                ride_photo.img_l = media.get_standard_resolution_url()
                ride_photo.img_t = media.get_thumbnail_url()
                db.session.commit()
            except InstagramAPIError as e:
                if e.status_code == 400:
                    self.logger.error("Skipping photo {0} for ride {1}; user is set to private".format(ride_photo))
                    del_q.append(ride_photo.id)
                else:
                    self.logger.exception("Error fetching instagram photo {0} (skipping)".format(ride_photo))


def main():
    FixPhotoUrls().run()


if __name__ == '__main__':
    main()