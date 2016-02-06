# Your settings

SQLALCHEMY_DATABASE_URI = 'mysql://freezing@localhost/freezing?charset=utf8mb4'

# Need a Strava Client ID and secret in order to authorize users
#STRAVA_CLIENT_ID = ''
#STRAVA_CLIENT_SECRETE = ''

# The competition time zone.  Naive date/time values will be assumed to be in this time zone.
BAFS_TIMEZONE = 'America/New_York'

# The strava team (club) IDs
BAFS_TEAMS = [] # This should be specified/overridden in local settings file.

# When does the competition start?
BAFS_START_DATE = '2015-01-01 00:00:00-05:00'

# When does the competition end?  (This can be an exact time; API will stop fetching after this time.)
BAFS_END_DATE = '2015-03-20 00:01:00-04:00'

# How many days after end of competition to upload rides?
BAFS_UPLOAD_GRACE_PERIOD_DAYS = 5

# Keywords to exclude from ride titles
BAFS_EXCLUDE_KEYWORDS = ['#NoBAFS']
