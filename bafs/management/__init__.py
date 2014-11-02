from django.db.models.signals import post_syncdb

class suppressed_sql_notes(object):
    '''
    Pimp a cursor object to suppress SQL notes and re-enable the
    original configuration when done.

    Use this in a with statement, like so:
      with suppressed_sql_notes(connection.cursor()) as cursor:
        cursor.execute('STUFF THAT YIELDS HARMLESS NOTICES')

    See django bug #12293 marked as WONTFIX.
    '''
    def __init__(self, cursor):
        self.cursor = cursor
    def __enter__(self):
        self.cursor.execute('''SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0;''')
        return self.cursor
    def __exit__(self, type, value, traceback):
        self.cursor.execute('''SET SQL_NOTES=@OLD_SQL_NOTES;''')
        
def post_syncdb_task(sender, **kwargs):
    from django.db import connection
    cursor = connection.cursor()
    
    with suppressed_sql_notes(cursor):
        cursor.execute("drop view if exists daily_scores")
        
    sql =   """
    create view daily_scores as
    select A.team_id, R.athlete_id, sum(R.distance) as distance,
    (sum(R.distance) + IF(sum(R.distance) >= 1.0, 10,0)) as points,
    date(R.start_date) as ride_date
    from rides R
    join athletes A on A.id = R.athlete_id
    group by R.athlete_id, A.team_id, date(R.start_date)
    ;
    """
    cursor.execute(sql);

    with suppressed_sql_notes(cursor):
        cursor.execute("drop view if exists _build_ride_daylight")
        
    sql = """
    create view _build_ride_daylight as
    select R.id as ride_id, date(R.start_date) as ride_date,
    sec_to_time(R.elapsed_time) as elapsed,
    sec_to_time(R.moving_time) as moving,
    TIME(R.start_date) as start_time,
    TIME(date_add(R.start_date, interval R.elapsed_time second)) as end_time,
    W.sunrise, W.sunset
    from rides R
    join ride_weather W on W.ride_id = R.id
    ;
    """
    cursor.execute(sql);
    
    with suppressed_sql_notes(cursor):
        cursor.execute("drop view if exists ride_daylight")
        
    sql = """
    create view ride_daylight as
    select ride_id, ride_date, start_time, end_time, sunrise, sunset, moving,
    IF(start_time < sunrise, LEAST(TIMEDIFF(sunrise, start_time), moving), sec_to_time(0)) as before_sunrise,
    IF(end_time > sunset, LEAST(TIMEDIFF(end_time, sunset), moving), sec_to_time(0)) as after_sunset
    from _build_ride_daylight
    ;
    """
    cursor.execute(sql);
    
from bafs import models as this_models
post_syncdb.connect(post_syncdb_task, sender=this_models)