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

from wx.ncdc import model

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
    name = None
    message = None
    
    def __init__(self, p1, p2=None):
        if p1 and p2:
            self.name = p1
            self.message = p2
            msg = '{0}: {1}'.format(self.name, self.message)
        else:
            self.message = p1
            msg = self.message
        super(Fault, self).__init__(msg)

class Client(object):
    
    base_url = urlparse.urlparse('http://www.ncdc.noaa.gov/cdo-services/services')
    
    def __init__(self, token, cache_dir=None):
        self.log = logging.getLogger('{0.__module__}.{0.__name__}'.format(self.__class__))
        self.token = token
        self.cache_dir = cache_dir
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _handle_protocol_error(self, response):
        """
        Parses the JSON response from the server, raising a :class:`stravatools.api.Fault` if the
        server returned an error.
        
        :param response: The response JSON
        :raises Fault: If the response contains an error. 
        """
        if 'cdoError' in response:
            raise Fault(response['name'], response['message'])
        return response
    
    def get(self, *args, **kwargs):
        """
        Construct a URL built on top of the base where args are the path elements
        and kwargs are any keywords.
        """
        path = self.base_url.path
        if not path.endswith('/'):
            path += '/'
        
        path_components = list(args)
        if path_components:
            if not path_components[-1].endswith('.json'):
                path_components[-1] += '.json'
             
        path += '/'.join(path_components)
        
        params = dict(token=self.token)
        params.update(kwargs)
        #query_params.update(urllib.urlencode(kwargs))
        #new_query_string = urllib.urlencode(query_params)
        
        url = urlparse.urlunsplit((self.base_url.scheme, self.base_url.netloc, path, self.base_url.query, self.base_url.fragment))
        
        self.log.debug("GET {0!r} with params {1!r}".format(url, params))
        raw = requests.get(url, params=params)
        raw.raise_for_status()
        self._handle_protocol_error(raw.json())
        
        # We add a 1s pause here, since otherwise we can get 503 errors from the server
        time.sleep(1.0)
        
        return raw

    def datasets(self):
        """
        Enumerate the datasets.
        """
        # We know this one is just a single page (always?), so we can probably make some shortcuts here?
        return self.get('datasets').json()['dataSetCollection']['dataSet']
    
    def locationsearch(self, lat, lon, radius=25, dataset='GHCND', page=1):
        data_getter = functools.partial(self.get, 'datasets', dataset, 'locationsearch', latitude=lat, longitude=lon, radius=radius)
        res = data_getter(page=page) 
        
        response_obj = res.json()
        collection = model.LocationSearchResultCollection(data_getter, response_obj)
        return collection
    
    def locationtypes(self):
        pass
    
    def locations(self):
        pass

    def stations(self):
        pass
    
    def _cache_dir(self, dataset, station):
        path = os.path.join(self.cache_dir, dataset, station)
        if not os.path.exists(path):
            os.makedirs(path)
        return path
    
    def _check_cache(self, dataset, station, date):
        data = None
        if self.cache_dir:
            basedir = self._cache_dir(dataset, station)
            filename = date.strftime('%Y-%m-%d') + '.json'
            filepath = os.path.join(basedir, filename)
            if os.path.exists(filepath):
                self.log.debug("Cache hit for {0}/{1}/{2}".format( dataset, station, date))
                with open(filepath, 'r') as fp:
                    data = json.loads(fp.read())
            else:
                self.log.debug("Cache miss for {0}/{1}/{2}".format( dataset, station, date))
                
        return data
             
    def _write_cache(self, dataset, station, date, response_json):
        if self.cache_dir:
            basedir = self._cache_dir(dataset, station)
            filename = date.strftime('%Y-%m-%d') + '.json'
            filepath = os.path.join(basedir, filename)
            with open(filepath, 'w') as fp:
                fp.write(json.dumps(response_json))
        
    def station_data(self, station, date, dataset='GHCND'):
        # /datasets/{dataSet}/stations/{station}/data
        data_getter = functools.partial(self.get, 'datasets', dataset, 'stations', station, 'data',
                                        year=date.strftime('%Y'),
                                        month=date.strftime('%m'),
                                        startday=date.strftime('%d'),
                                        endday=date.strftime('%d'))
        
        # Check cache
        data = self._check_cache(dataset, station, date)
        if not data:
            res = data_getter()
            data = res.json()
            self._write_cache(dataset, station, date, data)
            
        collection = model.DataCollection(data_getter, data)
        return collection

if __name__ == '__main__':
    import sys
    token = sys.argv[1]
    c = Client(token=sys.argv[1])
    desired_date = datetime(2013, 02, 25)
    search_results = c.locationsearch(lat=39.45536859, lon=-77.4142634, radius=50)
    desired_data = model.DesiredObservations(['TMIN', 'TMAX', 'PRCP', 'SNOW'])
    for r in search_results.results:
        if not desired_data.observations_needed:
            break
        if r.type == 'station':
            if desired_date <= r.maxDate and desired_date >= r.minDate:
                print "Getting station data for %r" % r
                coll = c.station_data(station=r.id, date=desired_date)
                desired_data.fill(coll)
                time.sleep(1.0)
            else:
                print "Skipping station %r because date doesn't match." % r
    else:
        print "Exhausted search without filling observations.  (missing = %r)" % (desired_data.observations_needed,)
        
    
    print desired_data.observations
    