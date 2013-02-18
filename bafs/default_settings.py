# Default settings

SQLALCHEMY_DATABASE_URI = 'mysql://bafs@localhost/bafs'
SQLALCHEMY_POOL_RECYCLE = 3600

# The strava team (club) IDs
BAFS_TEAMS = [19247, 19267, 19337, 19263, 8189, 19327, 19281, 19289, 19265, 19345, 20337]

# Any additional riders that are not affiliated with teams
BAFS_FREE_RIDERS = [75834]

# When does the competition start?
BAFS_START_DATE = '2013-01-01'

# Keywords to exclude from ride titles
BAFS_EXCLUDE_KEYWORDS = ['#NoBAFS']