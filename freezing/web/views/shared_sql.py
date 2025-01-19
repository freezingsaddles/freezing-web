"""
SQL queries used in more than one class. DRY 4EVA
"""

from sqlalchemy import text


def team_sleaze_query():
    return text(
        """
        select T.id, T.name as team_name, count(*) as num_sleaze_days
        from daily_scores D
        join lbd_athletes A on A.id = D.athlete_id
        join teams T on T.id = A.team_id
        where D.distance >= 1 and D.distance < 2
        group by T.id, T.name
        order by num_sleaze_days desc
        ;
    """
    )


def indiv_sleaze_query():
    return text(
        """
        select D.athlete_id, A.display_name as athlete_name, count(*) as num_sleaze_days
        from daily_scores D
        join lbd_athletes A on A.id = D.athlete_id
        where D.distance >= 1 and D.distance < 2
        group by D.athlete_id, athlete_name
        order by num_sleaze_days desc
        ;
    """
    )


def indiv_freeze_query():
    return text(
        """
        select athlete_id, athlete_name, SUM(max_daily_freeze_points) as freeze_points_total
        from (
            select athlete_id, athlete_name, ride_date, MAX(freeze_points) as max_daily_freeze_points
            from (
                select R.athlete_id, A.display_name as athlete_name, date(R.start_date) as ride_date, (11*(ATAN((R.distance+4)-2*PI())+1.4)-2.66)*(1.2+ATAN((32-W.ride_temp_start)/5)) as freeze_points
                from rides R
                join ride_weather W on W.ride_id = R.id
                join lbd_athletes A on A.id = R.athlete_id
            ) FP
            group by athlete_id, athlete_name, ride_date
        ) FPMax
        group by athlete_id, athlete_name
        order by freeze_points_total desc
        ;
    """
    )


def indiv_segment_query(join_miles=False):
    if join_miles:
        return text(
            """
            select aa.id, aa.athlete_name, aa.segment_rides, bb.dist from (select A.id, A.display_name as athlete_name, count(E.id) as segment_rides
            from lbd_athletes A
            join rides R on R.athlete_id = A.id
            join ride_efforts E on E.ride_id = R.id
            where E.segment_id = :segment_id
            group by A.id, A.display_name) aa
            join
            (select athlete_id, sum(distance) as dist from rides R group by athlete_id) bb
            on aa.id = bb.athlete_id
            order by aa.segment_rides desc;
        """
        )
    else:
        return text(
            """
            select A.id, A.display_name as athlete_name, count(E.id) as segment_rides
            from lbd_athletes A
            join rides R on R.athlete_id = A.id
            join ride_efforts E on E.ride_id = R.id
            where E.segment_id = :segment_id
            group by A.id, A.display_name
            order by segment_rides desc
            ;
        """
        )


def team_segment_query():
    return text(
        """
        select T.id, T.name as team_name, count(E.id) as segment_rides
        from rides R
        join lbd_athletes A on A.id = R.athlete_id
        join teams T on T.id = A.team_id
        join ride_efforts E on E.ride_id = R.id
        where E.segment_id = :segment_id and T.leaderboard_exclude=0
        group by T.id, T.name
        order by segment_rides desc
        ;
    """
    )


def team_leaderboard_query():
    return text(
        """
        select
          T.id as team_id,
          T.name as team_name,
          sum(DS.points) as total_score,
          sum(DS.distance) as total_distance,
          rank() over (order by sum(DS.points) desc) as "rank"
        from
          daily_scores DS join teams T on T.id = DS.team_id
        where not T.leaderboard_exclude
        group by T.id, T.name
        order by total_score desc
        ;
    """
    )
