from instagram import InstagramAPIError

from geoalchemy import WKTSpatialElement
from polyline.codec import PolylineCodec
from sqlalchemy import update, or_, and_

from bafs import db, model, data
from bafs.model import Ride, RideTrack, RidePhoto
from bafs.scripts import BaseCommand
from bafs.utils.insta import configured_instagram_client, photo_cache_path


class SyncActivityDetails(BaseCommand):
    @property
    def name(self):
        return 'sync-activity-details'

    def build_parser(self):
        parser = super(SyncActivityDetails, self).build_parser()
        parser.add_option("--athlete-id", dest="athlete_id",
                          help="Just sync rides for a specific athlete.",
                          metavar="STRAVA_ID")
        return parser

    def execute(self, options, args):

        q = db.session.query(model.Ride)

        # TODO: Construct a more complex query to catch photos_fetched=False, track_fetched=False, etc.
        q = q.filter(and_(or_(Ride.photos_fetched==False,
                              Ride.track_fetched==False),
                          Ride.private==False))

        if options.athlete_id:
            self.logger.info("Activity details for {}".format(options.athlete_id))
            q = q.filter(Ride.athlete_id == options.athlete_id)

        # TODO: Make this system better. Store the URLs to photos in the DB.
        # if photo_count == 1, then we don't need to fetch detail photos.
        #
        # Here is an Instagram photo, fetched using the /activities/<id>/photos API
        # [{u'activity_id': 414980300,
        #   u'activity_name': u'Pimmit Run CX',
        #   u'caption': u'Pimmit Run cx',
        #   u'created_at': u'2015-10-17T20:51:02Z',
        #   u'created_at_local': u'2015-10-17T16:51:02Z',
        #   u'id': 106409096,
        #   u'ref': u'https://instagram.com/p/88qaqZvrBI/',
        #   u'resource_state': 2,
        #   u'sizes': {u'0': [150, 150]},
        #   u'source': 2,
        #   u'type': u'InstagramPhoto',
        #   u'uid': u'1097938959360503880_297644011',
        #   u'unique_id': None,
        #   u'uploaded_at': u'2015-10-17T17:55:45Z',
        #   u'urls': {u'0': u'https://instagram.com/p/88qaqZvrBI/media?size=t'}}]

        # Here is a photo embedded in the activity:
        #
        # 'photos': {u'count': 1,
        #   u'primary': {u'id': None,
        #    u'source': 1,
        #    u'unique_id': u'35453b4b-0fc1-46fd-a824-a4548426b57d',
        #    u'urls': {u'100': u'https://dgtzuqphqg23d.cloudfront.net/Vvm_Mcfk1SP-VWdglQJImBvKzGKRJrHlNN4BqAqD1po-128x96.jpg',
        #     u'600': u'https://dgtzuqphqg23d.cloudfront.net/Vvm_Mcfk1SP-VWdglQJImBvKzGKRJrHlNN4BqAqD1po-768x576.jpg'}},
        #   u'use_primary_photo': False},

        # Here is when we have an Instagram photo as primary:
        #  u'photos': {u'count': 1,
        #   u'primary': {u'id': 106409096,
        #    u'source': 2,
        #    u'unique_id': None,
        #    u'urls': {u'100': u'https://instagram.com/p/88qaqZvrBI/media?size=t',
        #     u'600': u'https://instagram.com/p/88qaqZvrBI/media?size=l'}},
        #   u'use_primary_photo': False},

        for ride in q:
            self.logger.info("Writing out activity details for {0!r}".format(ride))

            try:
                client = data.StravaClientForAthlete(ride.athlete)
                activity = client.get_activity(ride.id)
                """ :type: stravalib.model.Activity """

                if ride.track_fetched == False:
                    if activity.map.polyline:
                        gps_track_points = PolylineCodec().decode(activity.map.polyline)
                        # LINESTRING(-80.3 38.2, -81.03 38.04, -81.2 37.89)
                        wkt_dims = ['{} {}'.format(lat, lon) for (lat,lon) in gps_track_points]
                        gps_track = WKTSpatialElement('LINESTRING({})'.format(', '.join(wkt_dims)))
                    else:
                        gps_track = None

                    if gps_track is not None:
                        ride_track = RideTrack()
                        ride_track.gps_track = gps_track
                        ride_track.ride_id = activity.id
                        db.session.merge(ride_track)

                    ride.track_fetched = True

                    db.session.commit()

                if not ride.photos_fetched:
                    pass

                    # if activity.photo_count > 1:
                    #
                    #
                    # try:
                    #     # Start by removing any existing photos for the ride.
                    #     if not options.rewrite:
                    #         # (This would be redundant if we already cleared the entire table.)
                    #         db.engine.execute(model.RidePhoto.__table__.delete().where(model.RidePhoto.ride_id == ride.id))
                    #
                    #     # Add the photos for this activity.
                    #     for p in client.get_activity_photos(ride.id):
                    #         try:
                    #             # TODO: Make caching configurable?
                    #             photo_cache_path(p.uid)
                    #
                    #             photo = model.RidePhoto(id=p.id,
                    #                                     ride_id=ride.id,
                    #                                     ref=p.ref,
                    #                                     caption=p.caption,
                    #                                     uid=p.uid)
                    #
                    #             self.logger.debug("Writing ride photo: {p_id}: {photo!r}".format(p_id=p.id,
                    #                                                                              photo=photo))
                    #             db.session.merge(photo)
                    #         except InstagramAPIError as e:
                    #             if e.status_code == 400:
                    #                 self.logger.debug(
                    #                     "Skipping photo {0} for ride {1}; user is set to private".format(p, ride))
                    #             else:
                    #                 self.logger.exception("Error fetching instagram photo {0}".format(p))
                    #
                    #     ride.photos_fetched = True
                    #     db.session.commit()  # @UndefinedVariable
                    # except:
                    #     self.logger.exception("Error adding photo for ride: {0}".format(ride))
                    #     continue

            except:
                self.logger.exception("Error fetching/writing activity {0}, athlete {1}".format(ride.id, ride.athlete))


def main():
    SyncActivityDetails().run()


if __name__ == '__main__':
    main()