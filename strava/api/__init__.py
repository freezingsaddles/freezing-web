import json
import logging

import requests

class Fault(Exception):
    """
    Container for exceptions raised by the remote server.
    """
    
class BaseServerProxy(object):
    """
    
    """
    server = 'www.strava.com'
    
    def __init__(self):
        self.log = logging.getLogger('{0.__name__}.{0.__module__}'.format(self.__class__))
    
    def _get(self, url, params=None):
        self.log.debug("GET {!r} with params {!r}".format(url, params))
        raw = requests.get(url, params=params)
        raw.raise_for_status()
        resp = self._handle_protocol_error(raw.json())
        return resp
    
    def _handle_protocol_error(self, response):
        """
        Parses the JSON response from the server, raising a :class:`stravatools.api.Fault` if the
        server returned an error.
        
        :param response: The response JSON
        :raises Fault: If the response contains an error. 
        """
        if 'error' in response:
            raise Fault(response['error'])
        return response
    