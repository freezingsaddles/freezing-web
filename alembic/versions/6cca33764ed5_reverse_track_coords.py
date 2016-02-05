"""reverse track coords

Revision ID: 6cca33764ed5
Revises: c206a3641567
Create Date: 2016-02-04 22:58:51.312968

"""

# revision identifiers, used by Alembic.
revision = '6cca33764ed5'
down_revision = 'c206a3641567'


import re

from alembic import op
import sqlalchemy as sa

_linestring_rx = re.compile('^LINESTRING\((.+)\)$')


def parse_linestring(wkt):
    """
    Parses LINESTRING WKT into a list of lon/lat (str) tuples.

    :param wkt: The WKT for the LINESTRING
    :type wkt: str`
    :return: List of (lon,lat) tuples.
    :rtype: list[(str,str)]
    """
    return [lonlat.split(' ') for lonlat in _linestring_rx.match(wkt).group(1).split(',')]


def linestring_wkt(points):
    wkt_dims = ['{} {}'.format(lon, lat) for (lon,lat) in points]
    return 'LINESTRING({})'.format(', '.join(wkt_dims))


def reverse_coordinates():
    conn = op.get_bind()
    results = conn.execute('select ride_id, AsWkt(gps_track) as gps_track from ride_tracks')
    i = 0
    for row in results:
        i += 1
        if i % 100 == 0:
            print("Row: {}".format(i))
        orig_points = parse_linestring(row['gps_track'])
        new_points = [(lon,lat) for (lat,lon) in orig_points]
        new_wkt = linestring_wkt(new_points)

        conn.execute('update ride_tracks set gps_track=ST_GeomFromText(%s) where ride_id=%s',
                     [new_wkt,
                      row['ride_id']
                      ])

def upgrade():
    reverse_coordinates()

def downgrade():
    upgrade()
