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

        parser.add_option("--rewrite", action="store_true", dest="rewrite", default=False,
                          help="Whether to rewrite the ride photo data already in database.")

        return parser

    def execute(self, options, args):

        if options.rewrite:
            db.engine.execute(model.RidePhoto.__table__.delete())
            db.session.query(model.Ride).update({"photos_fetched": False})

        q = db.session.query(model.Ride)
        q = q.filter_by(photos_fetched=False, private=False)

        for ride in q:
            self.logger.info("Writing out photos for {0!r}".format(ride))
            client = data.StravaClientForAthlete(ride.athlete)
            insta_client = configured_instagram_client()
            try:
                try:
                    # Start by removing any existing photos for the ride.
                    if not options.rewrite:
                        # (This would be redundant if we already cleared the entire table.)
                        db.engine.execute(model.RidePhoto.__table__.delete().where(model.RidePhoto.ride_id == ride.id))

                    # Add the photos for this activity.
                    for p in client.get_activity_photos(ride.id):
                        try:
                            # TODO: Make caching configurable?
                            photo_cache_path(p.uid)

                            photo = model.RidePhoto(id=p.id,
                                                    ride_id=ride.id,
                                                    ref=p.ref,
                                                    caption=p.caption,
                                                    uid=p.uid)

                            self.logger.debug("Writing ride photo: {p_id}: {photo!r}".format(p_id=p.id,
                                                                                             photo=photo))
                            db.session.merge(photo)
                        except InstagramAPIError as e:
                            if e.status_code == 400:
                                self.logger.debug(
                                    "Skipping photo {0} for ride {1}; user is set to private".format(p, ride))
                            else:
                                self.logger.exception("Error fetching instagram photo {0}".format(p))

                    ride.photos_fetched = True
                    db.session.commit()  # @UndefinedVariable
                except:
                    self.logger.exception("Error adding photo for ride: {0}".format(ride))
                    continue
            except:
                self.logger.exception("Error fetching/writing activity {0}, athlete {1}".format(ride.id, ride.athlete))


def main():
    SyncPhotos().run()