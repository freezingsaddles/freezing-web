'''
Created on Feb 10, 2013

@author: hans
'''
from datetime import timedelta

#from dateutil import rrule, parser 

from stravalib import Client
from stravalib import unithelper as uh

from django.shortcuts import render_to_response, redirect
from django.db import connection
from django import template
from django.core.urlresolvers import reverse

from bafs import data, settings
from bafs.utils import dbutil
from bafs.models import Team, Athlete
from people import people_list_users, people_show_person, ridedays

register = template.Library()

class AccessDenied(RuntimeError):
    pass

@register.filter
def groupnum(number):
    s = '%d' % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

def index():
    cursor = connection.cursor()
    q = """select count(*) as num_contestants from athletes WHERE team_id is not null"""
    cursor.execute(q)
    
    indiv_count_res = cursor.fetchone()
    contestant_count = indiv_count_res[0]

    q = """
        select count(*) as num_rides, sum(R.moving_time) as moving_time,
        sum(R.distance) as distance
        from rides R
        """
    
    cursor.execute(q)
    res = dbutil.dictfetchone(cursor)
    total_miles = int(res['distance'])
    total_hours = uh.timedelta_to_seconds(timedelta(seconds=int(res['moving_time']))) / 3600
    total_rides = res['num_rides']
     
    q = """
        select count(*) as num_rides, sum(R.moving_time) as moving_time
        from rides R 
        join ride_weather W on W.ride_id = R.id
        where W.ride_temp_avg < 32
        """
    
    cursor.execute(q)
    sub32_res = dbutil.dictfetchone(cursor)
    sub_freezing_hours = uh.timedelta_to_seconds(timedelta(seconds=int(sub32_res['moving_time']))) / 3600
    
    q = """
        select count(*) as num_rides, sum(R.moving_time) as moving_time
        from rides R 
        join ride_weather W on W.ride_id = R.id
        where W.ride_rain = 1
        """
    
    cursor.execute(q)
    rain_res = dbutil.dictfetchone(cursor)
    rain_hours = uh.timedelta_to_seconds(timedelta(seconds=int(rain_res['moving_time']))) / 3600
    
    q = """
        select count(*) as num_rides, sum(R.moving_time) as moving_time
        from rides R 
        join ride_weather W on W.ride_id = R.id
        where W.ride_snow = 1
        """
    
    cursor.execute(q)
    snow_res = dbutil.dictfetchone(cursor)
    snow_hours = uh.timedelta_to_seconds(timedelta(seconds=int(snow_res['moving_time']))) / 3600
    
    
    return render_to_response('index.html',
                              team_count=len(settings.BAFS_TEAMS),
                              contestant_count=contestant_count,
                              total_rides=total_rides,
                              total_hours=total_hours,
                              total_miles=total_miles,
                              rain_hours=rain_hours,
                              snow_hours=snow_hours,
                              sub_freezing_hours=sub_freezing_hours)

def join(request):
    c = Client()
    url = c.authorization_url(client_id=settings.STRAVA_CLIENT_ID,
                              redirect_uri=request.build_absolute_uri(reverse('authorization')),
                              approval_prompt='auto')
    return render_to_response('authorize.html', authorize_url=url)

def authorization(request):
    """
    Method called by Strava (redirect) that includes parameters.
    - state
    - code
    - error
    """
    error = request.args.get('error')
    state = request.args.get('state')
    if error:
        return render_to_response('authorization_error.html', error=error)
    else:
        code = request.args.get('code')
        client = Client()
        access_token = client.exchange_code_for_token(client_id=settings.STRAVA_CLIENT_ID,
                                                      client_secret=settings.STRAVA_CLIENT_SECRET,
                                                      code=code)
        # Use the now-authenticated client to get the current athlete
        strava_athlete = client.get_athlete()
        athlete_model = data.register_athlete(strava_athlete, access_token)
        multiple_teams = None
        no_teams = False
        team = None
        try:
            team = data.register_athlete_team(strava_athlete=strava_athlete, athlete_model=athlete_model)
        except data.MultipleTeamsError as multx:
            multiple_teams = multx.teams
        except data.NoTeamsError:
            no_teams = True
            
        
        return render_to_response('authorization_success.html', athlete=strava_athlete,
                                  team=team, multiple_teams=multiple_teams,
                                  no_teams=no_teams)

def leaderboard(request):
    return redirect(reverse('team_leaderboard'))

def team_leaderboard(request):
    return render_to_response('leaderboard/team.html')

def team_leaderboard_classic(request):
    # Get teams sorted by points
    cursor = connection.cursor()
    q = """
         select T.id as team_id, T.name as team_name, sum(DS.points) as total_score,
         sum(DS.distance) as total_distance
         from daily_scores DS 
         join teams T on T.id = DS.team_id 
         group by T.id, T.name
         order by total_score desc
         
         """
    
    cursor.execute(q)
    team_rows = dbutil.dictfetchall(cursor)
    
    q = """
         select A.id as athlete_id, A.team_id, A.display_name as athlete_name,
         sum(DS.points) as total_score, sum(DS.distance) as total_distance,
         count(DS.points) as days_ridden
         from daily_scores DS 
         join athletes A on A.id = DS.athlete_id
         group by A.id, A.display_name
         order by total_score desc
         """
    
    cursor.execute(q)
    team_members = {}
    for indiv_row in dbutil.dictfetchall(cursor): 
        team_members.setdefault(indiv_row['team_id'], []).append(indiv_row)
    
    for team_id in team_members:
        team_members[team_id] = reversed(sorted(team_members[team_id], key=lambda m: m['total_score']))
    
    return render_to_response('leaderboard/team_text.html', team_rows=team_rows, team_members=team_members)

def team_leaderboard_various():
    return render_to_response('leaderboard/team_various.html')

def indiv_leaderboard():
    return render_to_response('leaderboard/indiv.html')


def indiv_leaderboard_classic():
    cursor = connection.cursor()
    q = """
         select A.id as athlete_id, A.team_id, A.display_name as athlete_name,
         sum(DS.distance) as total_distance, sum(DS.points) as total_score,
         count(DS.points) as days_ridden
         from daily_scores DS 
         join athletes A on A.id = DS.athlete_id
         group by A.id, A.display_name
         order by total_score desc
         """
    cursor.execute(q)
    
    indiv_rows = dbutil.dictfetchall(cursor) 
    
    return render_to_response('leaderboard/indiv_text.html', indiv_rows=indiv_rows)

def indiv_leaderboard_various():
    return render_to_response('leaderboard/indiv_various.html')

def trends():
    return redirect(reverse('team_cumul_trend'))

def team_cumul_trend():
    return render_to_response('explore/team_cumul.html')

def team_weekly_points():
    return render_to_response('explore/team_weekly_points.html')

def indiv_elev_dist():
    return render_to_response('explore/indiv_elev_dist.html')

def riders_by_lowtemp():
    return render_to_response('explore/riders_by_lowtemp.html')

def list_users():
    return people_list_users()

def show_user(user_id):
    return people_show_person(user_id)
    
def ride_days():
    return ridedays()

def average_speed():
    cursor = connection.cursor()
    q = """
        select a.id, a.display_name, avg(b.average_speed) as speed from athletes a, rides b where a.id = b.athlete_id group by a.id order by speed;
        """
    cursor.execute(q)
    avgspeed = [(x['id'], x['display_name'], x['speed']) for x in dbutil.dictfetchall(cursor)]    
    return render_to_response('people/averagespeed.html', avg=avgspeed)
    

def average_distance():
    cursor = connection.cursor()
    q = """
        select a.id, a.display_name, avg(b.distance) as dist, count(distinct(date(b.start_date))) as distrides from athletes a, 
        rides b where a.id = b.athlete_id group by a.id order by dist;
        """
    cursor.execute(q)
    avgdist = [(x['id'], x['display_name'], x['dist']) for x in dbutil.dictfetchall(cursor) if x['distrides'] >= 10]    
    return render_to_response('people/distance.html', avg=avgdist) 


def billy_goat():
    cursor = connection.cursor()
    q = """
    select sum(a.elevation_gain) as elev,sum(a.distance) as dist, (sum(a.elevation_gain)/sum(a.distance)) as gainpermile, 
    c.name from rides a, athletes b, teams c where a.athlete_id=b.id and b.team_id=c.id group by c.name order by gainpermile desc;
    """
    cursor.execute(q)
    goat = [(x['name'], x['gainpermile'], x['dist'], x['elev']) for x in dbutil.dictfetchall(cursor)]
    return render_to_response('people/billygoat.html', data=goat)

def tortoise_team():
    cursor = connection.cursor()
    q = """
    select avg(a.average_speed) as spd,    c.name from rides a, athletes b, teams c where a.athlete_id=b.id and b.team_id=c.id group by c.name order by spd asc;
    """
    
    goat = [(x['name'], x['spd']) for x in dbutil.dictfetchall(cursor)]
    return render_to_response('people/tortoiseteam.html', data=goat)
    

def wknd():
    cursor = connection.cursor()
    q = """
        select A.id as athlete_id, A.display_name as athlete_name, sum(DS.points) as total_score, 
        sum(if((dayofweek(DS.ride_date)=7 or (dayofweek(DS.ride_date)=1)) , DS.points, 0)) as 'weekend',
        sum(if((dayofweek(DS.ride_date)<7 and (dayofweek(DS.ride_date)>1)) , DS.points, 0)) as 'weekday' 
        from daily_scores DS join athletes A on A.id = DS.athlete_id group by A.id
        order by weekend desc;
        """
    cursor.execute(q)
    weekend = [(x['athlete_id'], x['athlete_name'], x['total_score'], x['weekend'], x['weekday']) for x in dbutil.dictfetchall(cursor)]
    return render_to_response('people/weekend.html', data=weekend)

