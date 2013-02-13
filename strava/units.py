"""
Unit conversion functions.
"""

def meters_to_miles(meters):
    """
    Convert meters to miles.
    
    :param meters: Distance in meters. 
    :type meters: float
    
    :return: Equivalent number of miles.
    :rtype: float
    """
    return meters / 1609.34

def meters_to_feet(meters):
    """
    Convert meters to feet.
    
    :param meters: Distance in meters
    :type meters: float
    
    :return: Equivalent number of feet.
    :rtype: float
    """
    return meters * 3.28084

def metersps_to_mph(mps):
    """
    Convert meters-per-second to miles-per-hour.
    
    :rtype: float
    """
    return mps * 2.23694

def kph_to_mph(kph):
    """
    Convert kilometers-per-hour to miles-per-hour.
    
    :rtype: float
    """
    return kph / 1.60934
    