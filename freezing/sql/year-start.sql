/* Run this at the start of the new year to clear out last year's data */
use freezing;
/* hmm, putting this in a transaction made this take forever, and locked the site. */
/* begin; */
select count(*) from rides as rides_count;
select count(*) from athletes as athletes_count;
select count(*) from teams as teams_count;
select count(*) from ride_geo as ride_geo_count;
select count(*) from ride_weather as ride_weather_count;
/* Trying to truncate here was timing out, weirdly. That should be super fast, but it wasn't. Delete instead. */
select 'cleaning out rides';
delete from rides;
select 'cleaning out athletes';
delete from athletes;
select 'cleaning out teams';
delete from teams;
select 'cleaning out ride_geo';
delete from ride_geo;
select 'cleaning out ride_weather';
delete from ride_weather;
/* commit; */
/* don't forget to add the new competion's team back in after
   deleting last year's data, for example:

   insert into teams values (23456, 'Freezing Saddles 2020', 1);
*/
