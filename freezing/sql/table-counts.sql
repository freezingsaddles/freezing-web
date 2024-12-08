Select "_build_ride_daylight" as tablename, "VIEW" as tabletype,   count(*) from _build_ride_daylight Union 
Select "alembic_version" as tablename, "BASE TABLE" as tabletype,   count(*) from alembic_version Union 
Select "athletes" as tablename, "BASE TABLE" as tabletype,   count(*) from athletes Union 
Select "daily_scores" as tablename, "VIEW" as tabletype,   count(*) from daily_scores Union 
Select "daily_scores_elevation" as tablename, "VIEW" as tabletype,   count(*) from daily_scores_elevation Union 
Select "generator_16" as tablename, "VIEW" as tabletype,   count(*) from generator_16 Union 
Select "generator_256" as tablename, "VIEW" as tabletype,   count(*) from generator_256 Union 
Select "lbd_athletes" as tablename, "VIEW" as tabletype,   count(*) from lbd_athletes Union 
Select "ride_daylight" as tablename, "VIEW" as tabletype,   count(*) from ride_daylight Union 
Select "ride_efforts" as tablename, "BASE TABLE" as tabletype,   count(*) from ride_efforts Union 
Select "ride_geo" as tablename, "BASE TABLE" as tabletype,   count(*) from ride_geo Union 
Select "ride_photos" as tablename, "BASE TABLE" as tabletype,   count(*) from ride_photos Union 
Select "ride_start_end" as tablename, "VIEW" as tabletype,   count(*) from ride_start_end Union 
Select "ride_tracks" as tablename, "BASE TABLE" as tabletype,   count(*) from ride_tracks Union 
Select "ride_weather" as tablename, "BASE TABLE" as tabletype,   count(*) from ride_weather Union 
Select "rides" as tablename, "BASE TABLE" as tabletype,   count(*) from rides Union 
Select "team_daily_scores" as tablename, "VIEW" as tabletype,   count(*) from team_daily_scores Union 
Select "teams" as tablename, "BASE TABLE" as tabletype,   count(*) from teams Union 
Select "tribes" as tablename, "BASE TABLE" as tabletype,   count(*) from tribes Union 
Select "v_athlete_dist_freq" as tablename, "VIEW" as tabletype,   count(*) from v_athlete_dist_freq Union 
Select "v_athlete_dist_minmax" as tablename, "VIEW" as tabletype,   count(*) from v_athlete_dist_minmax Union 
Select "v_athlete_dist_totalfreq" as tablename, "VIEW" as tabletype,   count(*) from v_athlete_dist_totalfreq Union 
Select "v_athlete_dist_totalfreq_filled" as tablename, "VIEW" as tabletype,   count(*) from v_athlete_dist_totalfreq_filled Union 
Select "v_athlete_enumber" as tablename, "VIEW" as tabletype,   count(*) from v_athlete_enumber Union 
Select "v_athlete_enumber_candidates" as tablename, "VIEW" as tabletype,   count(*) from v_athlete_enumber_candidates Union 
Select "v_daily_dist_totals" as tablename, "VIEW" as tabletype,   count(*) from v_daily_dist_totals Union 
Select "variance_by_day" as tablename, "VIEW" as tabletype,   count(*) from variance_by_day Union 
Select "weekly_stats" as tablename, "VIEW" as tabletype,   count(*) from weekly_stats;
