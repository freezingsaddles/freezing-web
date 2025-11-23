"""
Functions for interacting with the datastore and the strava apis.
"""

from __future__ import division, unicode_literals

from freezing.model import meta
from freezing.model.orm import Athlete, Team

from freezing.web import config
from freezing.web.exc import MultipleTeamsError, NoTeamsError


def register_athlete(strava_athlete, token_dict):
    """
    Ensure specified athlete is added to database, returns athlete orm.

    :return: The added athlete model object.
    :rtype: :class:`bafs.orm.Athlete`
    """
    athlete = meta.scoped_session().get(Athlete, strava_athlete.id)
    if athlete is None:
        athlete = Athlete()
    athlete.id = strava_athlete.id
    athlete.name = "{0} {1}".format(
        strava_athlete.firstname, strava_athlete.lastname
    ).strip()
    # Temporary; we will update this in disambiguation phase.  (This isn't optimal; needs to be
    # refactored....
    #
    #     Where does the disambiguation phase get called now? Nowhere...
    #     so let's fix it here for now.
    #     * Do not override already set display_names.
    #     * Use a first name and last initial (if available).
    #     See also:
    #       https://github.com/freezingsaddles/freezing-web/issues/80
    #       https://github.com/freezingsaddles/freezing-web/issues/75
    #       https://github.com/freezingsaddles/freezing-web/issues/73
    #     - @obscurerichard]
    if athlete.display_name is None:
        if strava_athlete.lastname is None:
            athlete.display_name = strava_athlete.firstname
        else:
            athlete.display_name = "{0} {1}".format(
                strava_athlete.firstname.strip(),
                strava_athlete.lastname.strip(),
            )
    athlete.profile_photo = strava_athlete.profile

    athlete.access_token = token_dict["access_token"]
    athlete.refresh_token = token_dict["refresh_token"]
    athlete.expires_at = token_dict["expires_at"]
    meta.scoped_session().add(athlete)

    return athlete


def register_athlete_team(strava_athlete, athlete_model):
    """
    Updates db with configured team that matches the athlete's teams.

    Updates the passed-in Athlete model object with created/updated team.

    :param strava_athlete: The Strava athlete object returned by
        ``Client.get_athlete()``. (Type path changed in stravalib 2.x; the
        old ``stravalib.orm.Athlete`` reference is deprecated.)

    :param athlete_model: The athlete model object.
    :type athlete_model: :class:`bafs.orm.Athlete`

    :return: The :class:`bafs.orm.Team` object will be returned which matches
             configured teams.
    :rtype: :class:`bafs.orm.Team`

    :raise MultipleTeamsError: If this athlete is registered for multiple of
                               the configured teams.  That won't work.
    :raise NoTeamsError: If no teams match.
    """
    # TODO: This is redundant with freezingsaddles/freezing-sync which has a
    # very similar method in freezing/sync/data/athlete.py
    # Figure out how to DRY (Don't Repeat Yourself) for this code.

    all_teams = config.COMPETITION_TEAMS
    if strava_athlete.clubs is None:
        raise NoTeamsError(
            "Athlete {0} ({1} {2}): No clubs returned- {3}. {4}.".format(
                strava_athlete.id,
                strava_athlete.firstname,
                strava_athlete.lastname,
                "Full Profile Access required",
                "Please re-authorize",
            )
        )
    matches = [c for c in strava_athlete.clubs if c.id in all_teams]
    athlete_model.team = None
    if len(matches) > 1:
        # you can be on multiple teams
        # as long as only one is an official team
        matches = [c for c in matches if c.id not in config.OBSERVER_TEAMS]
    if len(matches) > 1:
        raise MultipleTeamsError(matches)
    if len(matches) == 0:
        # Fall back to main team if it is the only team they are in
        matches = [c for c in strava_athlete.clubs if c.id == config.MAIN_TEAM]
    if len(matches) == 0:
        raise NoTeamsError(
            "Athlete {0} ({1} {2}): {3} {4}".format(
                strava_athlete.id,
                strava_athlete.firstname,
                strava_athlete.lastname,
                "No teams matched ours. Teams defined:",
                strava_athlete.clubs,
            )
        )
    else:
        club = matches[0]
        # create the team row if it does not exist
        team = meta.scoped_session().get(Team, club.id)
        if team is None:
            team = Team()
        team.id = club.id
        team.name = club.name
        team.leaderboard_exclude = club.id in config.OBSERVER_TEAMS
        athlete_model.team = team
        meta.scoped_session().add(team)
        return team
