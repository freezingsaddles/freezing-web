import re
from collections import namedtuple

_point_rx = re.compile('^POINT\((.+)\)$')


LonLat = namedtuple('LonLat', ['lon', 'lat'])


def point_wkt(lon, lat):
    return 'POINT({lon} {lat})'.format(lon=lon, lat=lat)


def parse_point_wkt(wkt):
    (lon, lat) = _point_rx.match(wkt).group(1).split(' ')
    return LonLat(lon=lon, lat=lat)