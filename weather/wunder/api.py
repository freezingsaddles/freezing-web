'''
Created on Feb 27, 2013

@author: hans
'''
import os
import time
import json
import logging
import urlparse
import functools
import requests
from datetime import datetime

from weather.wunder.model import HistoryDay

"""
Here's the documentation:

Here is a specific station: http://www.ncdc.noaa.gov/cdo-services/services/datasets/GHCND/stations/GHCND:USC00327027/data?year=2010&month=1&token=FUYmBQlVXFZkbjrcUJudVPfjDWNLkJHu

Location search:
http://www.ncdc.noaa.gov/cdo-web/webservices/cdows_locationsearch
http://www.ncdc.noaa.gov/cdo-services/services/datasets/GHCND/locationsearch.xml?latitude=39.45536859&longitude=-77.4142634&radius=25&token=FUYmBQlVXFZkbjrcUJudVPfjDWNLkJHu
"""

class Fault(Exception):
    """
    Container for exceptions raised by the remote server.
    """
    type = None
    description = None
    
    def __init__(self, p1, p2=None):
        if p1 and p2:
            self.type = p1
            self.description = p2
            msg = '{0}: {1}'.format(self.type, self.description)
        else:
            self.description = p1
            msg = self.description
        super(Fault, self).__init__(msg)

class NoDataFound(RuntimeError):
    """
    Exception to raise when there is no data available.
    """

class Client(object):
    """
    A Weather Underground client.
    """
    
    # Here is an example URL:
    # http://api.wunderground.com/api/{api_key}/history_20130101/q/VA/Mc_Lean.json')
    base_url = urlparse.urlparse('http://api.wunderground.com/api/')
    
    def __init__(self, api_key, cache_dir=None, pause=1.0, cache_only=False):
        """
        :param api_key: The wunderground api key.
        :param cache_dir: The base directory for cache files.
        :param pause: How long to pause between requests (wunderground rate limit is 10 req/minute for developer accounts)
        :param cache_only: Whether to only use cached data (to avoid any further hits on server)
        """
        self.log = logging.getLogger('{0.__module__}.{0.__name__}'.format(self.__class__))
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.pause = pause
        self.cache_only = cache_only
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _handle_protocol_error(self, response):
        """
        Parses the JSON response from the server, raising a :class:`stravatools.api.Fault` if the
        server returned an error.
        
        :param response: The response JSON
        :raises Fault: If the response contains an error. 
        """
        if 'error' in response['response']:
            raise Fault(response['response']['error']['type'], response['response']['error']['description'])
        return response
    
    def get(self, *args, **kwargs):
        """
        Construct a URL built on top of the base where args are the path elements
        and kwargs are any keywords.
        """
        path = self.base_url.path
        if not path.endswith('/'):
            path += '/'
        
        path_components = [self.api_key] + list(args)
        if path_components:
            if not path_components[-1].endswith('.json'):
                path_components[-1] += '.json'
             
        path += '/'.join(path_components)
        
        params = dict()
        params.update(kwargs)
        #query_params.update(urllib.urlencode(kwargs))
        #new_query_string = urllib.urlencode(query_params)
        
        url = urlparse.urlunsplit((self.base_url.scheme, self.base_url.netloc, path, self.base_url.query, self.base_url.fragment))
        
        self.log.debug("GET {0!r} with params {1!r}".format(url, params))
        
        try:
            raw = requests.get(url, params=params)
            raw.raise_for_status()
            self._handle_protocol_error(raw.json())
            return raw
        finally:
            if self.pause: time.sleep(self.pause)
                
    def history(self, date, lat=None, lon=None, us_city=None):
        
        latlon_location_param = None
        us_city_location_param = None
        
        if lat and lon:
            latlon_location_param = '{0},{1}'.format(lat,lon)
        
        # Try for US city first, since this will be more reusable
        if us_city:
            # Split on comma to extract state
            if us_city.count(',') != 1:
                self.log.info("Unable to parse city/state for us city: {0}".format(us_city))
            else:
                city_parts = [part.strip() for part in us_city.split(',')]
                if len(city_parts[-1]) > 2: # US states are 2-chars
                    self.log.info("Doesn't look like a US city (state component > 2 chars): {0}".format(us_city))
                else:
                    us_city_location_param = city_parts[-1] + "/" + city_parts[0].replace(' ', '_')
        
        # Check both for cache, starting with more specific one
        for lp in (latlon_location_param, us_city_location_param):
            if lp is not None:
                data = self._check_cache(lp, date)
                if data:
                    break
        
        if data is None:
            if not self.cache_only:
                # Attempt to fetch for real (and cache), giving preference to the less specific 
                # for the sake of better reusability
                for lp in (us_city_location_param, latlon_location_param):
                    if lp is not None:
                        try:
                            res = self.get(date.strftime('history_%Y%m%d'), 'q', lp)
                        except Fault:
                            self.log.exception("Server fault trying to fetch weather for {0},{1}".format(lp, date))
                            continue
                        else:
                            break
                else:
                    # We tried all param options but each had an error
                    raise NoDataFound("Unable to retrieve weather for lat/lon={0}, us_city={1}, date={2}".format((lat,lon), us_city, date))
                
                # res should be defined if we get this far.
                data = res.json()
                self._write_cache(lp, date, data)
            else:
                raise NoDataFound("cache_only=True and no cached data found for lat/lon={0}, us_city={1}, date={2}".format((lat,lon), us_city, date))
        
        try:
            history_data = HistoryDay.from_json(data['history'])
        except:
            self.log.exception("Unable to parse data: {0!r}".format(data))
            raise
        
        return history_data
    
    def _cache_dir(self, location_param):
        path = os.path.join(self.cache_dir, location_param)
        if not os.path.exists(path):
            os.makedirs(path)
        return path
    
    def _check_cache(self, location_param, date):
        data = None
        if self.cache_dir:
            basedir = self._cache_dir(location_param)
            filename = date.strftime('%Y-%m-%d') + '.json'
            filepath = os.path.join(basedir, filename)
            if os.path.exists(filepath):
                self.log.debug("Cache hit for {0}/{1}".format( location_param, date))
                with open(filepath, 'r') as fp:
                    data = json.loads(fp.read())
            else:
                self.log.debug("Cache miss for {0}/{1}".format( location_param, date))
                
        return data
             
    def _write_cache(self, location_param, date, response_json):
        if self.cache_dir:
            basedir = self._cache_dir(location_param)
            filename = date.strftime('%Y-%m-%d') + '.json'
            filepath = os.path.join(basedir, filename)
            with open(filepath, 'w') as fp:
                fp.write(json.dumps(response_json))
        
    