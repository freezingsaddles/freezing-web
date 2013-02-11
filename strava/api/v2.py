import requests

from strava.api import BaseServerProxy

class V2ServerProxy(BaseServerProxy):
    """
    
    """
    auth_token = None
    
    @property
    def authenticated(self):
        return self.token is not None
    
    def authenticate(self, email, password):
        """
        """
        url = 'https://{server}/api/v2/authentication/login'.format(server=self.server)
        rawresp = requests.post(url, params=dict(email=email, password=password))
        resp = self._parse_response(rawresp)
        self.auth_token = resp['token']
        
    def get_ride(self, ride_id):
        """
        
        :param id: The id of the ride.
        
         {"id":"448459",
         "ride":
           {"id":448459,
            "name":"southern city loop",
            "start_date_local":"2011-04-19T08:16:56Z",
            "elapsed_time":5007,
            "moving_time":4787,
            "distance":33224.7,
            "average_speed":6.940609985377062,
            "elevation_gain":269.6,
            "location":"San Francisco, CA",
            "start_latlng":[37.77410821057856,-122.43948784656823],
            "end_latlng":[37.782084261998534,-122.40578069351614]},
            "version":"1303236084"}
        """
        url = "http://{server}/api/v2/rides/{id}".format(server=self.server, id=int(ride_id))
        return self._get(url)['ride']