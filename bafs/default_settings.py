# Your settings

SQLALCHEMY_DATABASE_URI = 'mysql://bafs@localhost/bafs?charset=utf8'

# Need a Strava Client ID and secret in order to authorize users
#STRAVA_CLIENT_ID = ''
#STRAVA_CLIENT_SECRETE = ''

# The strava team (club) IDs
BAFS_TEAMS = [8123]

# When does the competition start?
BAFS_START_DATE = '2013-01-01'

# When does the competition end?  (This can be an exact time; API will stop fetching after this time.)
BAFS_END_DATE = '2013-03-20 21:31:00-04:00'

# Keywords to exclude from ride titles
BAFS_EXCLUDE_KEYWORDS = ['#NoBAFS']