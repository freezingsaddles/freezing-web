"""reverse coordinates

Revision ID: c206a3641567
Revises: a77103b34b0b
Create Date: 2016-02-04 22:21:20.474487

"""

# revision identifiers, used by Alembic.
revision = 'c206a3641567'
down_revision = 'a77103b34b0b'

import re

from alembic import op
import sqlalchemy as sa

_point_rx = re.compile('^POINT\((.+)\)$')


def point_wkt(lon, lat):
    return 'POINT({lon} {lat})'.format(lon=lon, lat=lat)


def parse_point_wkt(wkt):
    (lon, lat) = _point_rx.match(wkt).group(1).split(' ')
    return (lon, lat)


def reverse_coordinates():
    conn = op.get_bind()
    results = conn.execute('select ride_id, AsWkt(start_geo) as start_geo, AsWkt(end_geo) as end_geo from ride_geo')
    for row in results:
        start_lat, start_lon = parse_point_wkt(row['start_geo'])
        end_lat, end_lon = parse_point_wkt(row['end_geo'])

        new_start_wkt = point_wkt(lon=start_lon, lat=start_lat)
        new_end_wkt = point_wkt(lon=end_lon, lat=end_lat)

        print('({} -> {}), ({} -> {})'.format(row['start_geo'], new_start_wkt, row['end_geo'], new_end_wkt))

        conn.execute('update ride_geo set start_geo=ST_GeomFromText(%s), end_geo=ST_GeomFromText(%s) where ride_id=%s',
                     [new_start_wkt,
                      new_end_wkt,
                      row['ride_id']
                      ])

def upgrade():
    reverse_coordinates()

def downgrade():
    upgrade()
