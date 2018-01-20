from instagram import InstagramAPIError

from freezing.model import meta
from freezing.model.orm import RidePhoto

from freezing.web.autolog import log

from freezing.web.scripts import BaseCommand
from freezing.web.utils.insta import configured_instagram_client


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
        #     meta.engine.execute(model.RidePhoto.__table__.delete())
        #     meta.session_factory().query(model.Ride).update({"photos_fetched": False})

        q = meta.session_factory().query(RidePhoto)
        q = q.filter_by(img_t=None)

        insta_client = configured_instagram_client()

        del_q = []
        for ride_photo in q:
            self.logger.debug("Updating URLs for photo {}".format(ride_photo))
            try:
                media = insta_client.media(ride_photo.id)
                ride_photo.img_l = media.get_standard_resolution_url()
                ride_photo.img_t = media.get_thumbnail_url()
                meta.session_factory().commit()
            except InstagramAPIError as e:
                if e.status_code == 400:
                    self.logger.error("Skipping photo {}; user is set to private".format(ride_photo))
                    del_q.append(ride_photo.id)
                else:
                    self.logger.exception("Error fetching instagram photo {0} (skipping)".format(ride_photo))

        if del_q:
            meta.engine.execute(RidePhoto.__table__.delete().where(RidePhoto.id.in_(del_q)))
            meta.session_factory().commit()

def main():
    FixPhotoUrls().run()


if __name__ == '__main__':
    main()