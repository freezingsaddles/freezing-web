import logging
from copy import copy
from datetime import datetime

from pytz import timezone

#        {
#        "date": {
#        "pretty": "12:52 AM EST on January 01, 2013",
#        "year": "2013",
#        "mon": "01",
#        "mday": "01",
#        "hour": "00",
#        "min": "52",
#        "tzname": "America/New_York"
#        },
#        "utcdate": {
#        "pretty": "5:52 AM GMT on January 01, 2013",
#        "year": "2013",
#        "mon": "01",
#        "mday": "01",
#        "hour": "05",
#        "min": "52",
#        "tzname": "UTC"
#        },
#        "tempm":"3.3", "tempi":"37.9","dewptm":"-2.2", "dewpti":"28.0","hum":"68","wspdm":"11.1", "wspdi":"6.9",
#        "wgustm":"-9999.0", "wgusti":"-9999.0","wdird":"200","wdire":"SSW","vism":"16.1", "visi":"10.0",
#        "pressurem":"1016.1", "pressurei":"30.01","windchillm":"0.4", "windchilli":"32.7","heatindexm":"-9999", 
#        "heatindexi":"-9999","precipm":"-9999.00", "precipi":"-9999.00","conds":"Overcast","icon":"cloudy",
#        "fog":"0","rain":"0","snow":"0","hail":"0","thunder":"0","tornado":"0",
#        "metar":"METAR KDCA 010552Z 20006KT 10SM FEW075 OVC130 03/M02 A3001 RMK AO2 SLP161 T00331022 10044 20033 56011" },

def build_date(dateobj):
    """ Builds a date from wundergound date structure. """ 
    year = int(dateobj['year'])
    mon = int(dateobj['mon'])
    day = int(dateobj['mday'])
    hour = int(dateobj['hour'])
    minute = int(dateobj['min'])
    return datetime(year, mon, day, hour, minute, 0, tzinfo=timezone(dateobj['tzname']))

def smart_cast(val, type_):
    if val is None or val == "" or (isinstance(val, str) and val.startswith('-99')):
        return None
    else:
        return type_(val)
            
class Observation(object):
    """
    A particular weather observation (e.g. there might be many during a day).
    """
    date = None
    temp = None
    windspeed = None
    windchill = None
    precip = None
    rain = None
    snow = None
    
    @classmethod
    def from_json(cls, jsonobj):
        """
        Constructs an observation from json object.
        """
        o = Observation()
        o.raw = jsonobj
        
        o.date = build_date(jsonobj['date'])
        
        o.temp = smart_cast(jsonobj['tempi'], float)
        o.windspeed = smart_cast(jsonobj['wspdi'], float)
        o.windchill = smart_cast(jsonobj['windchilli'], float)
        o.precip = smart_cast(jsonobj['precipi'], float)
        
        o.rain = smart_cast(jsonobj['rain'], lambda x: bool(int(x)))
        o.snow = smart_cast(jsonobj['snow'], lambda x: bool(int(x)))
        
        return o
    
    def __repr__(self):
        return '<{0} date={1} temp={2}>'.format(self.__class__.__name__, self.date, self.temp)
    
class HistoryDay(object):
    """
    History for a single day.
    """
    date = None
    
    def __init__(self):
        self.log = logging.getLogger('{0.__module__}.{0.__name__}'.format(self.__class__))
        self.observations = []

    def find_first_before(self, date):
        """ Finds the first observation before the specified date. """
        date = date.replace(tzinfo=self.date.tzinfo)
        # Iterate over the observations until the date is later, then return the previous
        assert len(self.observations) > 0
        prev = None
        for o in self.observations:
            if o.date > date:
                break
            prev = o
        else:
            self.log.warning("Exhausted all observations, didn't find any later than {0} (will use closest)".format(date))
    
        if prev is None:
            self.log.warning("Couldn't find a weather observation earlier than {0}".format(date))
            prev = o # last object from iter?
            
        return prev
        
    def find_next_after(self, date):
        """ Finds the next observation after the specified date. """
        assert len(self.observations) > 0
        date = date.replace(tzinfo=self.date.tzinfo)
        # Iterate over the observations until the date is later, then return the previous
        prev = None
        for o in reversed(self.observations):
            if o.date < date:
                break
            prev = o
        else:
            self.log.warning("Exhausted all observations, didn't find any earlier than {0} (will use closest)".format(date))
    
        if prev is None:
            self.log.warning("No weather observations after {0} (will use closest)".format(date))
            prev = o # last object from iter
            
        return prev
    
    def find_observations_within(self, start_date, end_date):
        """
        Returns all observations whose dates fall in between the specified start and end dates.
        """
        # We are assuming that the observations will always be same tz as this [day] history object.
        # (That should be safe??)
        if start_date.tzinfo is None:
            start_date = copy(start_date).replace(tzinfo=self.date.tzinfo)
        if end_date.tzinfo is None:
            end_date = copy(end_date).replace(tzinfo=self.date.tzinfo)
        
        between_dates = False
        matched = []
        for o in self.observations:
            if o.date >= start_date:
                between_dates = True
            if o.date > end_date:
                # It's possible that we are setting this to False before we've even gotten any matches.
                between_dates = False
                break
                
            if between_dates:
                matched.append(o)
        
        # May be empty list
        return matched
    
    def find_nearest_observation(self, date):
        """
        Gets the observation closest in time (before or after) to specified date. 
        """
        if date.tzinfo is None:
            date = copy(date).replace(tzinfo=self.date.tzinfo)
            
        # Iterate over all the observations and compare to date, keeping track
        # of the observations that has the minimum delta.
        min_delta = None
        best_obs = None
        for o in self.observations:
            if date > o.date:
                delta = (date - o.date).seconds
            elif date < o.date:
                delta = (o.date - date).seconds
            else:
                delta = 0
            if min_delta is None or delta < min_delta:
                min_delta = delta
                best_obs = o
                
        return best_obs
            
    @classmethod
    def from_json(cls, jsonobj):
        """
        Initialize object from JSON object.
        """ 
        h = HistoryDay()
        
        h.raw = jsonobj
        
        h.date = build_date(jsonobj['date'])
        
        observations = []
        for obsdata in jsonobj['observations']:
            obs = Observation.from_json(obsdata)
            observations.append(obs)

        h.observations = sorted(observations, key=lambda el: el.date) # Ensure they are sorted by date (maybe the default?)
        
        # Sometimes there is no daily summary
        if jsonobj.get('dailysummary'):
            h.min_temp = smart_cast(jsonobj['dailysummary'][0]['mintempi'], float)
            h.max_temp = smart_cast(jsonobj['dailysummary'][0]['maxtempi'], float)
        else:
            h.min_temp = min([o.temp for o in h.observations])
            h.max_temp = max([o.temp for o in h.observations])
                
        return h