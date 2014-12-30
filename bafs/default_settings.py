# Your settings

SQLALCHEMY_DATABASE_URI = 'mysql://bafs@localhost/bafs?charset=utf8'

# Need a Strava Client ID and secret in order to authorize users
#STRAVA_CLIENT_ID = ''
#STRAVA_CLIENT_SECRETE = ''

# The strava team (club) IDs
BAFS_TEAMS = [
              46292, # Team 0
              46380, # Team 1
              46386, # Team 2
              46418, # Team 3
              46225, # Team 4
              46334, # Team 5
              46402, # Team 6
              46246, # Team 7
              46209, # Team 8
              46202, # Team 9
              ]

# When does the competition start?
BAFS_START_DATE = '2015-01-01'

# When does the competition end?  (This can be an exact time; API will stop fetching after this time.)
BAFS_END_DATE = '2015-03-20 00:01:00-04:00'

# How many days after end of competition to upload rides?
BAFS_UPLOAD_GRACE_PERIOD_DAYS = 5

# Keywords to exclude from ride titles
BAFS_EXCLUDE_KEYWORDS = ['#NoBAFS']
