/* Thanks https://www.techbrothersit.com/2018/12/how-to-get-record-counts-for-all-tables.html 
   these were good bones, and just needed a little GROUP_CONCAT love*/
SELECT GROUP_CONCAT(
	'select ',
    '"', table_name, '" as tablename, ',
    '"', table_type, '" as tabletype, ',
    'count(*) from ', table_name 
    SEPARATOR '\nunion ') 
    AS ''
FROM 
 INFORMATION_SCHEMA.TABLES 
WHERE table_schema = 'freezing';
