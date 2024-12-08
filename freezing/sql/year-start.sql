/* Run this at the start of the new year to clear out last year's data */
use freezing;
/* hmm, putting this in a transaction made this take forever, and locked the site. */
/* begin; */
select count(*) from athletes as athletes_count;
select count(*) from rides as rides_count;
select count(*) from ride_efforts as ride_efforts_count;
select count(*) from ride_geo as ride_geo_count;
select count(*) from ride_photos as ride_photos_count;
select count(*) from ride_tracks as ride_tracks_count;
select count(*) from ride_weather as ride_weather_count;
select count(*) from teams as teams_count;
select 'cleaning out ride_efforts';
truncate ride_efforts;
select 'cleaning out ride_geo';
truncate ride_geo;
select 'cleaning out ride_photos';
truncate ride_photos;
select 'cleaning out ride_tracks';
truncate ride_tracks;
select 'cleaning out ride_weather';
truncate ride_weather:;
select 'cleaning out rides';
delete from rides;
select 'cleaning out athletes';
delete from athletes;
select 'cleaning out teams';
delete from teams;
/* commit; */
/* don't forget to add the new competion's team back in after
   deleting last year's data, for example:

   insert into teams values (23456, 'Freezing Saddles 2021', 1);
*/
