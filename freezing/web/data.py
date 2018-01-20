"""
Functions for interacting with the datastore and the strava apis.
"""
from __future__ import division, unicode_literals
import re
import logging

from instagram import InstagramAPIError, InstagramClientError

from polyline.codec import PolylineCodec

from sqlalchemy import and_
from geoalchemy import WKTSpatialElement

from requests.exceptions import HTTPError

from stravalib import Client
from stravalib import model as strava_model
from stravalib import unithelper

from freezing.model import meta, orm
from freezing.model.orm import Athlete, Ride, RideGeo, RideEffort, RidePhoto, RideTrack, Team

from freezing.web import app
from freezing.web.autolog import log
from freezing.web.exc import InvalidAuthorizationToken, NoTeamsError, MultipleTeamsError, DataEntryError
from freezing.web.utils import insta, wktutils


class StravaClientForAthlete(Client):
    """
    Creates a StravaClient for the specified athlete.
    """

    def __init__(self, athlete):
        if not isinstance(athlete, Athlete):
            athlete = meta.session_factory().query(Athlete).get(athlete)
        super(StravaClientForAthlete, self).__init__(access_token=athlete.access_token, rate_limit_requests=True)


def register_athlete(strava_athlete, access_token):
    """
    Ensure specified athlete is added to database, returns athlete orm.

    :return: The added athlete model object.
    :rtype: :class:`bafs.orm.Athlete`
    """
    athlete = meta.session_factory().query(Athlete).get(strava_athlete.id)
    if athlete is None:
        athlete = Athlete()
    athlete.id = strava_athlete.id
    athlete.name = '{0} {1}'.format(strava_athlete.firstname, strava_athlete.lastname).strip()
    # Temporary; we will update this in disambiguation phase.  (This isn't optimal; needs to be
    # refactored....)
    athlete.display_name = strava_athlete.firstname
    athlete.profile_photo = strava_athlete.profile

    athlete.access_token = access_token
    meta.session_factory().add(athlete)
    # We really shouldn't be committing here, since we want to disambiguate names after registering
    meta.session_factory().commit()

    return athlete


def disambiguate_athlete_display_names():
    q = meta.session_factory().query(orm.Athlete)
    q = q.filter(orm.Athlete.access_token != None)
    athletes = q.all()

    # Ok, here is the plan; bin these things together based on firstname and last initial.
    # Then iterate over each bin and if there are multiple entries, find the least number
    # of letters to make them all different. (we should be able to use set intersection
    # to check for differences within the bins?)

    def firstlast(name):
        name_parts = a.name.split(' ')
        fname = name_parts[0]
        if len(name_parts) < 2:
            lname = None
        else:
            lname = name_parts[-1]
        return (fname, lname)

    athletes_bin = {}
    for a in athletes:
        (fname, lname) = firstlast(a.name)
        if lname is None:
            # We only care about people with first and last names for this exercise
            # key = fname
            continue
        else:
            key = '{0} {1}'.format(fname, lname[0])
        athletes_bin.setdefault(key, []).append(a)

    for (name_key, athletes) in athletes_bin.items():
        shortest_lname = min([firstlast(a.name)[1] for a in athletes], key=len)
        required_length = None
        for i in range(len(shortest_lname)):
            # Calculate fname + lname-of-x-chars for each athlete.
            # If unique, then use this number and update the model objects
            candidate_short_lasts = [firstlast(a.name)[1][:i + 1] for a in athletes]
            if len(set(candidate_short_lasts)) == len(candidate_short_lasts):
                required_length = i + 1
                break

        if required_length is not None:
            for a in athletes:
                fname, lname = firstlast(a.name)
                log.debug("Converting '{fname} {lname}' -> '{fname} {minlname}".format(fname=fname,
                                                                                       lname=lname,
                                                                                       minlname=lname[
                                                                                                :required_length]))
                a.display_name = '{0} {1}'.format(fname, lname[:required_length])
        else:
            log.debug("Unable to find a minimum lastname; using full lastname.")
            # Just use full names
            for a in athletes:
                fname, lname = firstlast(a.name)
                a.display_name = '{0} {1}'.format(fname, lname[:required_length])

    # Update the database with new values
    meta.session_factory().commit()


def register_athlete_team(strava_athlete, athlete_model):
    """
    Updates db with configured team that matches the athlete's teams.

    Updates the passed-in Athlete model object with created/updated team.

    :param strava_athlete: The Strava model object for the athlete.
    :type strava_athlete: :class:`stravalib.orm.Athlete`

    :param athlete_model: The athlete model object.
    :type athlete_model: :class:`bafs.orm.Athlete`

    :return: The :class:`bafs.orm.Team` object will be returned which matches
             configured teams.
    :rtype: :class:`bafs.orm.Team`

    :raise MultipleTeamsError: If this athlete is registered for multiple of
                               the configured teams.  That won't work.
    :raise NoTeamsError: If no teams match.
    """
    assert isinstance(strava_athlete, strava_model.Athlete)
    assert isinstance(athlete_model, Athlete)

    all_teams =  app.config['BAFS_TEAMS']
    log.info("Checking {0!r} against {1!r}".format(strava_athlete.clubs, all_teams))
    try:
        matches = [c for c in strava_athlete.clubs if c.id in all_teams]
        log.debug("Matched: {0!r}".format(matches))
        athlete_model.team = None
        if len(matches) > 1:
            # you can be on multiple teams as long as only one is an official team
            matches = [c for c in matches if c.id not in app.config['BAFS_OBSERVER_TEAMS']]
        if len(matches) > 1:
            log.info("Multiple teams matched.")
            raise MultipleTeamsError(matches)
        elif len(matches) == 0:
            raise NoTeamsError()
        else:
            club = matches[0]
            # create the team row if it does not exist
            team = meta.session_factory().query(Team).get(club.id)
            if team is None:
                team = Team()
            team.id = club.id
            team.name = club.name
            team.leaderboard_exclude = club.id in app.config['BAFS_OBSERVER_TEAMS']
            athlete_model.team = team
            meta.session_factory().add(team)
            return team
    finally:
        meta.session_factory().commit()


def get_team_name(club_id):
    """
    Convenience function to return the club name, given the ID.
    """
    raise NotImplementedError()
    # client = V1ServerProxy()
    # return client.get_club(club_id)['name']


def list_rides(athlete, start_date=None, end_date=None, exclude_keywords=None):
    """
    List all of the rides for individual athlete.

    :param athlete: The Athlete model object.
    :type athlete: bafs.orm.Athlete

    :param start_date: The date to start listing rides.
    :type start_date: datetime.date

    :param exclude_keywords: A list of keywords to use for excluding rides from the results (e.g. "#NoBAFS")
    :type exclude_keywords: list

    :return: list of activity objects for rides in reverse chronological order.
    :rtype: list[stravalib.orm.Activity]
    """
    client = StravaClientForAthlete(athlete)

    if exclude_keywords is None:
        exclude_keywords = []

    # Remove tz, since we are dealing with local times for activities
    end_date = end_date.replace(tzinfo=None)

    def is_excluded(activity):
        activity_end_date = (activity.start_date_local + activity.elapsed_time)
        if end_date and activity_end_date > end_date:
            log.info(
                "Skipping ride {0} ({1!r}) because date ({2}) is after competition end date ({3})".format(activity.id,
                                                                                                          activity.name,
                                                                                                          activity_end_date,
                                                                                                          end_date))
            return True

        for keyword in exclude_keywords:
            if keyword.lower() in activity.name.lower():
                log.info("Skipping ride {0} ({1!r}) due to presence of exlusion keyword: {2!r}".format(activity.id,
                                                                                                       activity.name,
                                                                                                       keyword))
                return True
        else:
            return False

    try:
        activities = client.get_activities(after=start_date, limit=None)  # type: List[stravalib.orm.Activity]
        filtered_rides = [a for a in activities if
                          ((a.type == strava_model.Activity.RIDE or a.type == strava_model.Activity.EBIKERIDE)
                          and not a.manual and not a.trainer and not is_excluded(a))]
    except HTTPError as e:
        if u'access_token' in e.message:  # A bit of a kludge, but don't have a way of hooking into the response processing earlier.
            raise InvalidAuthorizationToken("Invalid authrization token for {}".format(athlete))

        # Otherwise just fall-through and re-raise same exception.
        raise e

    return filtered_rides


def timedelta_to_seconds(td):
    """
    Converts a timedelta to total seconds.
    (This is built-in in Python 2.7)
    """
    # we ignore microseconds for this
    if not td:
        return None
    return td.seconds + td.days * 24 * 3600


def write_ride(activity):
    """
    Takes the specified activity and writes it to the database.

    :param activity: The Strava :class:`stravalib.orm.Activity` object.
    :type activity: stravalib.orm.Activity

    :return: A tuple including the written Ride model object, whether to resync segment efforts, and whether to resync photos.
    :rtype: bafs.orm.Ride
    """

    if activity.start_latlng:
        start_geo = WKTSpatialElement('POINT({lon} {lat})'.format(lat=activity.start_latlng.lat,
                                                                  lon=activity.start_latlng.lon))
    else:
        start_geo = None

    if activity.end_latlng:
        end_geo = WKTSpatialElement('POINT({lon} {lat})'.format(lat=activity.end_latlng.lat,
                                                                lon=activity.end_latlng.lon))
    else:
        end_geo = None

    athlete_id = activity.athlete.id

    # Fail fast for invalid data (this can happen with manual-entry rides)
    assert activity.elapsed_time is not None
    assert activity.moving_time is not None
    assert activity.distance is not None

    # Find the model object for that athlete (or create if doesn't exist)
    athlete = meta.session_factory().query(Athlete).get(athlete_id)
    if not athlete:
        # The athlete has to exist since otherwise we wouldn't be able to query their rides
        raise ValueError("Somehow you are attempting to write rides for an athlete not found in the database.")

    if start_geo is not None or end_geo is not None:
        ride_geo = RideGeo()
        ride_geo.start_geo = start_geo
        ride_geo.end_geo = end_geo
        ride_geo.ride_id = activity.id
        meta.session_factory().merge(ride_geo)

    ride = meta.session_factory().query(Ride).get(activity.id)
    new_ride = (ride is None)
    if ride is None:
        ride = Ride(activity.id)

    # Check to see if we need to pull down efforts for this ride
    if new_ride:
        ride.detail_fetched = False  # Just to be explicit

        if not activity.manual:
            ride.track_fetched = False

        # photo_count refers to instagram photos
        if activity.photo_count > 1:
            ride.photos_fetched = False
        else:
            ride.photos_fetched = None

    else:
        if round(ride.distance, 2) != round(float(unithelper.miles(activity.distance)), 2):
            log.info("Queing resync of details for activity {0!r}: distance mismatch ({1} != {2})".format(activity,
                                                                                                          ride.distance,
                                                                                                          unithelper.miles(activity.distance)))
            ride.detail_fetched = False
            ride.track_fetched = False

    ride.athlete = athlete


    update_ride_from_activity(strava_activity=activity, ride=ride)


    meta.session_factory().add(ride)

    return ride


def update_ride_from_activity(strava_activity, ride):
    """
    Refactoring to just set ride properties from the Strava Activity object.

    :param strava_activity: The Strava Activyt
    :type strava_activity: stravalib.orm.Activity
    :param ride: The ride model object.
    :type ride: Ride
    """
     # Should apply to both new and preexisting rides ...
    # If there are multiple instagram photos, then request syncing of non-primary photos too.

    if strava_activity.photo_count > 1 and ride.photos_fetched is None:


        log.debug("Scheduling non-primary photos sync for {!r}".format(ride))
        ride.photos_fetched = False

    ride.private = bool(strava_activity.private)
    ride.name = strava_activity.name
    ride.start_date = strava_activity.start_date_local

    # We need to round so that "1.0" miles in strava is "1.0" miles when we convert back from meters.
    ride.distance = round(float(unithelper.miles(strava_activity.distance)), 3)

    ride.average_speed = float(unithelper.mph(strava_activity.average_speed))
    ride.maximum_speed = float(unithelper.mph(strava_activity.max_speed))
    ride.elapsed_time = timedelta_to_seconds(strava_activity.elapsed_time)
    ride.moving_time = timedelta_to_seconds(strava_activity.moving_time)

    location_parts = []
    if strava_activity.location_city:
        location_parts.append(strava_activity.location_city)
    if strava_activity.location_state:
        location_parts.append(strava_activity.location_state)
    location_str = ', '.join(location_parts)

    ride.location = location_str

    ride.commute = strava_activity.commute
    ride.trainer = strava_activity.trainer
    ride.manual = strava_activity.manual
    ride.elevation_gain = float(unithelper.feet(strava_activity.total_elevation_gain))
    ride.timezone = str(strava_activity.timezone)

    # # Short-circuit things that might result in more obscure db errors later.
    if ride.elapsed_time is None:
        raise DataEntryError("Activities cannot have null elapsed time.")

    if ride.moving_time is None:
        raise DataEntryError("Activities cannot have null moving time.")

    if ride.distance is None:
        raise DataEntryError("Activities cannot have null distance.")

    log.debug("Writing ride for {athlete!r}: \"{ride!r}\" on {date}".format(athlete=ride.athlete.name,
                                                                        ride=ride.name,
                                                                        date=ride.start_date.strftime('%m/%d/%y')))


def write_ride_efforts(strava_activity, ride):
    """
    Writes out all effort associated with a ride to the database.

    :param strava_activity: The :class:`stravalib.orm.Activity` that is associated with this effort.
    :type strava_activity: :class:`stravalib.orm.Activity`

    :param ride: The db model object for ride.
    :type ride: :class:`bafs.orm.Ride`
    """
    assert isinstance(strava_activity, strava_model.Activity)
    assert isinstance(ride, Ride)

    try:
        # Start by removing any existing segments for the ride.
        meta.engine.execute(RideEffort.__table__.delete().where(RideEffort.ride_id == strava_activity.id))

        # Then add them back in
        for se in strava_activity.segment_efforts:
            effort = RideEffort(id=se.id,
                                ride_id=strava_activity.id,
                                elapsed_time=timedelta_to_seconds(se.elapsed_time),
                                segment_name=se.segment.name,
                                segment_id=se.segment.id)

            log.debug("Writing ride effort: {se_id}: {effort!r}".format(se_id=se.id,
                                                                        effort=effort.segment_name))

            meta.session_factory().add(effort)
            meta.session_factory().flush()

        ride.efforts_fetched = True

    except:
        log.exception("Error adding effort for ride: {0}".format(ride))
        raise


# def write_ride_track(strava_activity, ride):
#     """
#     Store GPS track for activity as LINESTRING in db.
#
#     :param strava_activity: The Strava :class:`stravalib.orm.Activity` object.
#     :type strava_activity: :class:`stravalib.orm.Activity`
#
#     :param ride: The db model object for ride.
#     :type ride: :class:`bafs.orm.Ride`
#     """
#     # Start by removing any existing segments for the ride.
#     meta.engine.execute(RideTrack.__table__.delete().where(RideTrack.ride_id == strava_activity.id))
#
#     if strava_activity.map.polyline:
#         latlon_points = PolylineCodec().decode(strava_activity.map.polyline)
#         lonlat_points = [(lon,lat) for (lat,lon) in latlon_points]
#         gps_track = WKTSpatialElement(wktutils.linestring_wkt(lonlat_points))
#     else:
#         gps_track = None
#
#     if gps_track is not None:
#         ride_track = RideTrack()
#         ride_track.gps_track = gps_track
#         ride_track.ride_id = strava_activity.id
#         meta.session_factory().add(ride_track)


def write_ride_streams(streams, ride):
    """
    Store GPS track for activity as LINESTRING in db.

    :param streams: The Strava :class:`stravalib.orm.Activity` object.
    :type streams: list[stravalib.orm.Stream]

    :param ride: The db model object for ride.
    :type ride: :class:`bafs.orm.Ride`
    """
    try:
        streams_dict = {s.type: s for s in streams}
        """ :type: dict[str,stravalib.orm.Stream] """
        lonlat_points = [(lon,lat) for (lat,lon) in streams_dict['latlng'].data]

        if not lonlat_points:
            raise ValueError("No data points in latlng streams.")
    except (KeyError, ValueError) as x:
        log.info("No GPS track for activity {} (skipping): {}".format(ride, x), exc_info=log.isEnabledFor(logging.DEBUG))
        ride.track_fetched = None
    else:
        # Start by removing any existing segments for the ride.
        meta.engine.execute(RideTrack.__table__.delete().where(RideTrack.ride_id == ride.id))

        gps_track = WKTSpatialElement(wktutils.linestring_wkt(lonlat_points))

        ride_track = RideTrack()
        ride_track.gps_track = gps_track
        ride_track.ride_id = ride.id
        ride_track.elevation_stream = streams_dict['altitude'].data
        ride_track.time_stream = streams_dict['time'].data
        meta.session_factory().add(ride_track)

    ride.track_fetched = True


# try:
#     self.logger.info("Writing out GPS track for {!r}".format(ride))
#     data.write_ride_track(strava_activity, ride)
# except:
#     self.logger.error("Error writing track for activity {0}, athlete {1}".format(ride.id, ride.athlete),
#                       exc_info=self.logger.isEnabledFor(logging.DEBUG))
#     raise


def _write_instagram_photo_primary(photo, ride):
    """
    Writes an instagram primary photo to db.

    :param photo: The primary photo from an activity.
    :type photo: stravalib.orm.ActivityPhotoPrimary
    :param ride: The db model object for ride.
    :type ride: bafs.orm.Ride
    :return: The newly added ride photo object.
    :rtype: bafs.orm.RidePhoto
    """
    # Here is when we have an Instagram photo as primary:
    #  u'photos': {u'count': 1,
    #   u'primary': {u'id': 106409096,
    #    u'source': 2,
    #    u'unique_id': None,
    #    u'urls': {u'100': u'https://instagram.com/p/88qaqZvrBI/media?size=t',
    #     u'600': u'https://instagram.com/p/88qaqZvrBI/media?size=l'}},
    #   u'use_prima ry_photo': False},


    media = None

    # This doesn't work any more; Instagram changed their API to use OAuth.
    #insta_client = insta.configured_instagram_client()
    #shortcode = re.search(r'/p/([^/]+)/', photo.urls['100']).group(1)
    # try:
    #     #log.debug("Fetching Instagram media for shortcode: {}".format(shortcode))
    #     media = insta_client.media_shortcode(shortcode)
    # except (InstagramAPIError, InstagramClientError) as e:
    #     if e.status_code == 400:
    #         log.warning("Instagram photo {} for ride {}; user is set to private".format(shortcode, ride))
    #     elif e.status_code == 404:
    #         log.warning("Photo {} for ride {}; shortcode not found".format(shortcode, ride))
    #     else:
    #         log.exception("Error fetching instagram photo {}".format(photo))

    p = RidePhoto()

    if media:
        p.id = media.id
        p.ref = media.link
        p.img_l = media.get_standard_resolution_url()
        p.img_t = media.get_thumbnail_url()
        if media.caption:
            p.caption = media.caption.text
    else:
        p.id = photo.id
        p.ref = re.match(r'(.+/)media\?size=.$', photo.urls['100']).group(1)
        p.img_l = photo.urls['600']
        p.img_t = photo.urls['100']

    p.ride_id = ride.id
    p.primary = True
    p.source = photo.source

    log.debug("Writing (primary) Instagram ride photo: {!r}".format(p))

    meta.session_factory().add(p)
    meta.session_factory().flush()

    return p

def _write_strava_photo_primary(photo, ride):
    """
    Writes a strava native (source=1) primary photo to db.

    :param photo: The primary photo from an activity.
    :type photo: stravalib.orm.ActivityPhotoPrimary
    :param ride: The db model object for ride.
    :type ride: bafs.orm.Ride
    :return: The newly added ride photo object.
    :rtype: bafs.orm.RidePhoto
    """
    # 'photos': {u'count': 1,
    #   u'primary': {u'id': None,
    #    u'source': 1,
    #    u'unique_id': u'35453b4b-0fc1-46fd-a824-a4548426b57d',
    #    u'urls': {u'100': u'https://dgtzuqphqg23d.cloudfront.net/Vvm_Mcfk1SP-VWdglQJImBvKzGKRJrHlNN4BqAqD1po-128x96.jpg',
    #     u'600': u'https://dgtzuqphqg23d.cloudfront.net/Vvm_Mcfk1SP-VWdglQJImBvKzGKRJrHlNN4BqAqD1po-768x576.jpg'}},
    #   u'use_primary_photo': False},

    if not photo.urls:
        log.warning("Photo {} present, but has no URLs (skipping)".format(photo))
        return None

    p = RidePhoto()
    p.id = photo.unique_id
    p.primary = True
    p.source = photo.source
    p.ref = None
    p.img_l = photo.urls['600']
    p.img_t = photo.urls['100']
    p.ride_id = ride.id

    log.debug("Writing (primary) Strava ride photo: {}".format(p))

    meta.session_factory().add(p)
    meta.session_factory().flush()
    return p


def write_ride_photo_primary(strava_activity, ride):
    """
    Store primary photo for activity from the main detail-level activity.

    :param strava_activity: The Strava :class:`stravalib.orm.Activity` object.
    :type strava_activity: :class:`stravalib.orm.Activity`

    :param ride: The db model object for ride.
    :type ride: bafs.orm.Ride
    """
    # If we have > 1 instagram photo, then we don't do anything.
    if strava_activity.photo_count > 1:
        log.debug("Ignoring basic sync for {} since there are > 1 instagram photos.")
        return

    # Start by removing any priamry photos for this ride.
    meta.engine.execute(RidePhoto.__table__.delete().where(and_(RidePhoto.ride_id == strava_activity.id,
                                                              RidePhoto.primary == True)))

    primary_photo = strava_activity.photos.primary

    if primary_photo:
        if primary_photo.source == 1:
            _write_strava_photo_primary(primary_photo, ride)
        else:
            _write_instagram_photo_primary(primary_photo, ride)


def write_ride_photos_nonprimary(activity_photos, ride):
    """
    Writes out non-primary photos (currently only instagram) associated with a ride to the database.

    :param activity_photos: Photos for an activity.
    :type activity_photos: list[stravalib.orm.ActivityPhoto]

    :param ride: The db model object for ride.
    :type ride: bafs.orm.Ride
    """
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

    meta.engine.execute(RidePhoto.__table__.delete().where(and_(RidePhoto.ride_id == ride.id,
                                                              RidePhoto.primary == False)))

    insta_client = insta.configured_instagram_client()

    for activity_photo in activity_photos:

        # If it's already in the db, then skip it.
        existing = meta.session_factory().query(RidePhoto).get(activity_photo.uid)
        if existing:
            log.info("Skipping photo {} because it's already in database: {}".format(activity_photo, existing))
            continue

        try:
            media = insta_client.media(activity_photo.uid)

            photo = RidePhoto(id=activity_photo.uid,
                              ride_id=ride.id,
                              ref=activity_photo.ref,
                              caption=activity_photo.caption)

            photo.img_l = media.get_standard_resolution_url()
            photo.img_t = media.get_thumbnail_url()

            meta.session_factory().add(photo)

            log.debug("Writing (non-primary) ride photo: {p_id}: {photo!r}".format(p_id=photo.id, photo=photo))

            meta.session_factory().flush()
        except (InstagramAPIError, InstagramClientError) as e:
            if e.status_code == 400:
                log.warning("Skipping photo {0} for ride {1}; user is set to private".format(activity_photo, ride))
            elif e.status_code == 404:
                log.warning("Skipping photo {0} for ride {1}; not found".format(activity_photo, ride))
            else:
                log.exception("Error fetching instagram photo {0} (skipping)".format(activity_photo))


    ride.photos_fetched = True
