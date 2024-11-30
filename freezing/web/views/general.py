"""
Created on Feb 10, 2013

@author: hans
"""

from datetime import datetime

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from freezing.model import meta
from freezing.model.orm import Ride, RidePhoto
from sqlalchemy import text
from stravalib import Client

from freezing.web import app, config, data
from freezing.web.autolog import log
from freezing.web.exc import MultipleTeamsError, NoTeamsError
from freezing.web.utils import auth

blueprint = Blueprint("general", __name__)


class AccessDenied(RuntimeError):
    pass


@app.template_filter("groupnum")
def groupnum(number):
    s = "%d" % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ",".join(reversed(groups))


@blueprint.route("/")
def index():
    q = text("""select count(*) as num_contestants from lbd_athletes""")

    indiv_count_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    contestant_count = indiv_count_res["num_contestants"]

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time,
                  coalesce(sum(R.distance),0) as distance
                from rides R
                ;
            """
    )

    all_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    total_miles = int(all_res["distance"])
    total_hours = int(all_res["moving_time"]) / 3600
    total_rides = all_res["num_rides"]

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_temp_avg < 32
                ;
            """
    )

    sub32_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    sub_freezing_hours = int(sub32_res["moving_time"]) / 3600

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_rain = 1
                ;
            """
    )

    rain_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    rain_hours = int(rain_res["moving_time"]) / 3600

    q = text(
        """
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_snow = 1
                ;
            """
    )

    snow_res = meta.scoped_session().execute(q).fetchone()  # @UndefinedVariable
    snow_hours = int(snow_res["moving_time"]) / 3600

    # Grab some recent photos
    photos = (
        meta.scoped_session()
        .query(RidePhoto)
        .join(Ride)
        .order_by(Ride.start_date.desc())
        .limit(11)
    )

    return render_template(
        "index.html",
        team_count=len(config.COMPETITION_TEAMS),
        contestant_count=contestant_count,
        total_rides=total_rides,
        total_hours=total_hours,
        total_miles=total_miles,
        rain_hours=rain_hours,
        snow_hours=snow_hours,
        sub_freezing_hours=sub_freezing_hours,
        photos=photos,
    )


@blueprint.route("/logout")
def logout():
    session.clear()
    return redirect(url_for(".index"))


@blueprint.route("/authorize")
@blueprint.route("/login")
def join():
    c = Client()
    public_url = c.authorization_url(
        client_id=config.STRAVA_CLIENT_ID,
        redirect_uri=url_for(".authorization", _external=True),
        approval_prompt="auto",
        scope=["read", "activity:read", "profile:read_all"],
    )
    private_url = c.authorization_url(
        client_id=config.STRAVA_CLIENT_ID,
        redirect_uri=url_for(".authorization", _external=True),
        approval_prompt="auto",
        scope=["read_all", "activity:read_all", "profile:read_all"],
    )
    return render_template(
        "authorize.html",
        public_authorize_url=public_url,
        private_authorize_url=private_url,
    )


@blueprint.route("/authorization")
def authorization():
    """
    Method called by Strava (redirect) that includes parameters.
    - state
    - code
    - error
    """
    error = request.args.get("error")
    if error:
        return render_template(
            "authorization_error.html",
            error=error,
        )
    else:
        code = request.args.get("code")
        client = Client()
        token_dict = client.exchange_code_for_token(
            client_id=config.STRAVA_CLIENT_ID,
            client_secret=config.STRAVA_CLIENT_SECRET,
            code=code,
        )
        # Use the now-authenticated client to get the current athlete
        strava_athlete = client.get_athlete()
        athlete_model = data.register_athlete(strava_athlete, token_dict)
        if not athlete_model:
            return render_template(
                "authorization_error.html",
                error="ATHLETE_NOT_FOUND",
            )
        multiple_teams = None
        no_teams = False
        team = None
        message = None
        try:
            team = data.register_athlete_team(
                strava_athlete=strava_athlete,
                athlete_model=athlete_model,
            )
        except MultipleTeamsError as multx:
            multiple_teams = multx.teams
            message = multx
        except NoTeamsError as noteamx:
            no_teams = True
            message = noteamx
        if not no_teams:
            auth.login_athlete(strava_athlete)
        # Thanks https://stackoverflow.com/a/32926295/424301 for the hint on tzinfo aware compares
        after_competition_start = (
            datetime.now(config.START_DATE.tzinfo) > config.START_DATE
        )
        return render_template(
            "authorization_success.html",
            after_competition_start_start=after_competition_start,
            athlete=strava_athlete,
            competition_teams_assigned=len(config.COMPETITION_TEAMS) > 0,
            team=team,
            message=message,
            main_team_page=f"https://strava.com/clubs/{config.MAIN_TEAM}",
            multiple_teams=multiple_teams,
            no_teams=no_teams,
            rides_url=url_for("user.rides"),
        )


@blueprint.route("/webhook", methods=["GET"])
def webhook_challenge():
    client = Client()
    strava_request = {
        k: request.args.get(k)
        for k in ("hub.challenge", "hub.mode", "hub.verify_token")
    }
    log.info("Webhook challenge: {}".format(strava_request))
    challenge_resp = client.handle_subscription_callback(
        strava_request, verify_token=config.STRAVA_VERIFY_TOKEN
    )
    return jsonify(challenge_resp)


@blueprint.route("/webhook", methods=["POST"])
def webhook_activity():
    log.info("Activity webhook: {}".format(request.json))
    return jsonify()


@blueprint.route("/explore")
def trends():
    return redirect(url_for(".team_cumul_trend"))


@blueprint.route("/explore/team_weekly")
def team_weekly_points():
    return render_template(
        "explore/team_weekly_points.html",
    )


@blueprint.route("/explore/indiv_elev_dist")
def indiv_elev_dist():
    return render_template(
        "explore/indiv_elev_dist.html",
    )


@blueprint.route("/explore/distance_by_lowtemp")
def riders_by_lowtemp():
    return render_template(
        "explore/distance_by_lowtemp.html",
    )


@blueprint.route("/explore/team_cumul")
def team_cumul_trend():
    return render_template(
        "explore/team_cumul.html",
    )
