import re
from collections import namedtuple

_point_rx = re.compile("^POINT\((.+)\)$")
_linestring_rx = re.compile("^LINESTRING\((.+)\)$")

LonLat = namedtuple("LonLat", ["lon", "lat"])


def point_wkt(lon, lat):
    return "POINT({lon} {lat})".format(lon=lon, lat=lat)


def parse_point_wkt(wkt):
    (lon, lat) = _point_rx.match(wkt).group(1).split(" ")
    return LonLat(lon=lon, lat=lat)


def parse_linestring(wkt):
    """
    Parses LINESTRING WKT into a list of lon/lat (str) tuples.

    :param wkt: The WKT for the LINESTRING
    :type wkt: str`
    :return: List of (lon,lat) tuples.
    :rtype: list[(str,str)]
    """
    return [
        lonlat.split(" ") for lonlat in _linestring_rx.match(wkt).group(1).split(",")
    ]


def linestring_wkt(points):
    wkt_dims = ["{} {}".format(lon, lat) for (lon, lat) in points]
    return "LINESTRING({})".format(", ".join(wkt_dims))
