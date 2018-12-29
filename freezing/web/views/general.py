'''
Created on Feb 10, 2013

@author: hans
'''
from datetime import timedelta

from flask import render_template, redirect, url_for, request, Blueprint, session, jsonify
from sqlalchemy import text
from stravalib import Client
from stravalib import unithelper as uh

from freezing.model import meta
from freezing.model.orm import Athlete, RidePhoto, Ride

from freezing.web import app, data, config
from freezing.web.utils import auth
from freezing.web.autolog import log
from freezing.web.exc import MultipleTeamsError, NoTeamsError

blueprint = Blueprint('general', __name__)

class AccessDenied(RuntimeError):
    pass

@app.template_filter('groupnum')
def groupnum(number):
    s = '%d' % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

@blueprint.route("/")
def index():
    q = text ("""select count(*) as num_contestants from lbd_athletes""")

    indiv_count_res = meta.scoped_session().execute(q).fetchone() # @UndefinedVariable
    contestant_count = indiv_count_res['num_contestants']

    q = text ("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time,
                  coalesce(sum(R.distance),0) as distance
                from rides R
                ;
            """)

    all_res = meta.scoped_session().execute(q).fetchone() # @UndefinedVariable
    total_miles = int(all_res['distance'])
    total_hours = uh.timedelta_to_seconds(timedelta(seconds=int(all_res['moving_time']))) / 3600
    total_rides = all_res['num_rides']

    q = text ("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_temp_avg < 32
                ;
            """)

    sub32_res = meta.scoped_session().execute(q).fetchone() # @UndefinedVariable
    sub_freezing_hours = uh.timedelta_to_seconds(timedelta(seconds=int(sub32_res['moving_time']))) / 3600

    q = text ("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_rain = 1
                ;
            """)

    rain_res = meta.scoped_session().execute(q).fetchone() # @UndefinedVariable
    rain_hours = uh.timedelta_to_seconds(timedelta(seconds=int(rain_res['moving_time']))) / 3600

    q = text ("""
                select count(*) as num_rides, coalesce(sum(R.moving_time),0) as moving_time
                from rides R
                join ride_weather W on W.ride_id = R.id
                where W.ride_snow = 1
                ;
            """)

    snow_res = meta.scoped_session().execute(q).fetchone() # @UndefinedVariable
    snow_hours = uh.timedelta_to_seconds(timedelta(seconds=int(snow_res['moving_time']))) / 3600


    # Grab some recent photos
    photos = meta.scoped_session().query(RidePhoto).join(Ride).order_by(Ride.start_date.desc()).limit(11)

    return render_template('index.html',
                           team_count=len(config.COMPETITION_TEAMS),
                           contestant_count=contestant_count,
                           total_rides=total_rides,
                           total_hours=total_hours,
                           total_miles=total_miles,
                           rain_hours=rain_hours,
                           snow_hours=snow_hours,
                           sub_freezing_hours=sub_freezing_hours,
                           photos=photos,
                           competition_title=config.COMPETITION_TITLE)

@blueprint.route("/login")
def login():
    c = Client()
    url = c.authorization_url(client_id=config.STRAVA_CLIENT_ID,
                              redirect_uri=url_for('.logged_in', _external=True),
                              approval_prompt='auto')
    return render_template('login.html',
			   authorize_url=url,
                           competition_title=config.COMPETITION_TITLE)

@blueprint.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('.index'))


@blueprint.route("/strava-oauth")
def logged_in():
    """
    Method called by Strava (redirect) that includes parameters.
    - state
    - code
    - error
    """
    error = request.args.get('error')
    state = request.args.get('state')
    if error:
        return render_template('login_error.html',
                               error=error,
                               competition_title=config.COMPETITION_TITLE)
    else:
        code = request.args.get('code')
        client = Client()
        access_token = client.exchange_code_for_token(client_id=config.STRAVA_CLIENT_ID,
                                                      client_secret=config.STRAVA_CLIENT_SECRET,
                                                      code=code)
        # Use the now-authenticated client to get the current athlete
        strava_athlete = client.get_athlete()

        athlete_model = meta.scoped_session().query(Athlete).get(strava_athlete.id)
        if not athlete_model:
            return render_template('login_error.html',
                                   error="ATHLETE_NOT_FOUND",
                                   competition_title=config.COMPETITION_TITLE)

        multiple_teams = None
        no_teams = False
        team = None
        try:
            team = data.register_athlete_team(strava_athlete=strava_athlete, athlete_model=athlete_model)
        except MultipleTeamsError as multx:
            multiple_teams = multx.teams
        except NoTeamsError:
            no_teams = True

        if not no_teams:
            auth.login_athlete(strava_athlete)
            return redirect(url_for('user.rides'))
        else:
            return render_template('login_results.html', athlete=strava_athlete,
                                   team=team, multiple_teams=multiple_teams,
                                   no_teams=no_teams,
                                   competition_title=config.COMPETITION_TITLE)

@blueprint.route("/authorize")
def join():
    c = Client()
    public_url = c.authorization_url(client_id=config.STRAVA_CLIENT_ID,
                                     redirect_uri=url_for('.authorization', _external=True),
                                     approval_prompt='auto')
    private_url = c.authorization_url(client_id=config.STRAVA_CLIENT_ID,
                                      redirect_uri=url_for('.authorization', _external=True),
                                      approval_prompt='auto',
                                      scope='view_private')
    return render_template('authorize.html',
                           public_authorize_url=public_url,
                           private_authorize_url=private_url,
                           competition_title=config.COMPETITION_TITLE)

@blueprint.route("/authorization")
def authorization():
    """
    Method called by Strava (redirect) that includes parameters.
    - state
    - code
    - error
    """
    error = request.args.get('error')
    state = request.args.get('state')
    if error:
        return render_template('authorization_error.html',
                               error=error,
                               competition_title=config.COMPETITION_TITLE)
    else:
        code = request.args.get('code')
        client = Client()
        access_token = client.exchange_code_for_token(client_id=config.STRAVA_CLIENT_ID,
                                                      client_secret=config.STRAVA_CLIENT_SECRET,
                                                      code=code)
        # Use the now-authenticated client to get the current athlete
        strava_athlete = client.get_athlete()
        athlete_model = data.register_athlete(strava_athlete, access_token)
        multiple_teams = None
        no_teams = False
        team = None
        try:
            team = data.register_athlete_team(strava_athlete=strava_athlete, athlete_model=athlete_model)
        except MultipleTeamsError as multx:
            multiple_teams = multx.teams
        except NoTeamsError:
            no_teams = True

        return render_template('authorization_success.html', athlete=strava_athlete,
                               team=team, multiple_teams=multiple_teams,
                               no_teams=no_teams,
                               competition_title=config.COMPETITION_TITLE)


@blueprint.route("/webhook", methods=['GET'])
def webhook_challenge():
    client = Client()
    strava_request = {k: request.args.get(k) for k in ('hub.challenge', 'hub.mode', 'hub.verify_token')}
    log.info("Webhook challenge: {}".format(strava_request))
    challenge_resp = client.handle_subscription_callback(strava_request, verify_token=config.STRAVA_VERIFY_TOKEN)
    return jsonify(challenge_resp)


@blueprint.route("/webhook", methods=['POST'])
def webhook_activity():
    log.info("Activity webhook: {}".format(request.json))
    return jsonify()


@blueprint.route("/explore")
def trends():
    return redirect(url_for('.team_cumul_trend'))


@blueprint.route("/explore/team_weekly")
def team_weekly_points():
    return render_template('explore/team_weekly_points.html',
                           competition_title=config.COMPETITION_TITLE)

@blueprint.route("/explore/indiv_elev_dist")
def indiv_elev_dist():
    return render_template('explore/indiv_elev_dist.html',
                           competition_title=config.COMPETITION_TITLE)

@blueprint.route("/explore/distance_by_lowtemp")
def riders_by_lowtemp():
    return render_template('explore/distance_by_lowtemp.html',
                           competition_title=config.COMPETITION_TITLE)


@blueprint.route("/explore/team_cumul")
def team_cumul_trend():
    return render_template('explore/team_cumul.html',
                           competition_title=config.COMPETITION_TITLE)
